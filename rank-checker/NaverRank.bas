Attribute VB_Name = "NaverRank"
' =====================================================================
'  네이버 쇼핑 키워드 순위 조회 매크로
'  - '설정' 시트에 API 키 / 내 스토어명 / 상품ID 입력
'  - '순위조회' 시트 A열(2행부터)에 키워드 입력 후 CheckRanks 실행
' =====================================================================
Option Explicit

Private Const SHEET_SETTINGS As String = "설정"
Private Const SHEET_MAIN As String = "순위조회"
Private Const SHEET_LOG As String = "기록"
Private Const API_URL As String = "https://openapi.naver.com/v1/search/shop.json"
Private Const PAGE_SIZE As Long = 100        ' API 1회 최대 100개
Private Const API_MAX_START As Long = 1000   ' API start 최대값
Private Const WEB_PAGE_SIZE As Long = 40     ' 네이버 쇼핑 화면 1페이지 상품 수

Public Sub CheckRanks()
    Dim wsSet As Worksheet, ws As Worksheet, wsLog As Worksheet
    Set wsSet = ThisWorkbook.Worksheets(SHEET_SETTINGS)
    Set ws = ThisWorkbook.Worksheets(SHEET_MAIN)
    On Error Resume Next
    Set wsLog = ThisWorkbook.Worksheets(SHEET_LOG)
    On Error GoTo 0

    Dim clientId As String, clientSecret As String, mallName As String
    Dim productIds As String, maxRank As Long
    clientId = Trim$(CStr(wsSet.Range("B2").Value))
    clientSecret = Trim$(CStr(wsSet.Range("B3").Value))
    mallName = Trim$(CStr(wsSet.Range("B4").Value))
    productIds = CStr(wsSet.Range("B5").Value)
    maxRank = Val(wsSet.Range("B6").Value)
    If maxRank <= 0 Or maxRank > API_MAX_START Then maxRank = API_MAX_START

    If clientId = "" Or clientSecret = "" Then
        MsgBox "'설정' 시트에 Client ID / Client Secret 을 입력해 주세요.", vbExclamation
        Exit Sub
    End If
    If mallName = "" And Trim$(productIds) = "" Then
        MsgBox "'설정' 시트에 내 스토어명 또는 상품ID 중 하나는 입력해 주세요.", vbExclamation
        Exit Sub
    End If

    Dim idList As Variant
    idList = SplitIds(productIds)

    Dim lastRow As Long, r As Long, done As Long
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    If lastRow < 2 Then
        MsgBox "'순위조회' 시트 A열 2행부터 키워드를 입력해 주세요.", vbExclamation
        Exit Sub
    End If

    Application.ScreenUpdating = False
    Application.Cursor = xlWait

    For r = 2 To lastRow
        Dim keyword As String
        keyword = Trim$(CStr(ws.Cells(r, "A").Value))
        If keyword <> "" Then
            Application.StatusBar = "순위 조회 중... (" & (r - 1) & "/" & (lastRow - 1) & ") " & keyword
            ws.Range(ws.Cells(r, "B"), ws.Cells(r, "H")).ClearContents

            Dim rank As Long, title As String, price As String, pid As String, errMsg As String
            rank = FindRank(keyword, clientId, clientSecret, mallName, idList, maxRank, _
                            title, price, pid, errMsg)

            If errMsg <> "" Then
                ws.Cells(r, "B").Value = "오류"
                ws.Cells(r, "H").Value = errMsg
            ElseIf rank > 0 Then
                ws.Cells(r, "B").Value = rank
                ws.Cells(r, "C").Value = ((rank - 1) \ WEB_PAGE_SIZE + 1) & "페이지 " & _
                                         ((rank - 1) Mod WEB_PAGE_SIZE + 1) & "번째"
                ws.Cells(r, "D").Value = title
                ws.Cells(r, "E").Value = Val(price)
                ws.Cells(r, "F").NumberFormat = "@"
                ws.Cells(r, "F").Value = pid
            Else
                ws.Cells(r, "B").Value = "순위밖"
                ws.Cells(r, "H").Value = maxRank & "위 안에 없음"
            End If
            ws.Cells(r, "G").Value = Now

            If Not wsLog Is Nothing Then
                Dim lr As Long
                lr = wsLog.Cells(wsLog.Rows.Count, "A").End(xlUp).Row + 1
                wsLog.Cells(lr, "A").Value = Now
                wsLog.Cells(lr, "B").Value = keyword
                wsLog.Cells(lr, "C").Value = ws.Cells(r, "B").Value
                wsLog.Cells(lr, "D").Value = title
            End If
            done = done + 1
        End If
    Next r

    Application.StatusBar = False
    Application.Cursor = xlDefault
    Application.ScreenUpdating = True
    MsgBox done & "개 키워드 순위 조회 완료!", vbInformation
End Sub

' 키워드 검색 결과에서 내 상품의 순위를 찾는다. 없으면 0.
Private Function FindRank(ByVal keyword As String, ByVal clientId As String, ByVal clientSecret As String, _
                          ByVal mallName As String, ByVal idList As Variant, ByVal maxRank As Long, _
                          ByRef outTitle As String, ByRef outPrice As String, ByRef outPid As String, _
                          ByRef outErr As String) As Long
    Dim start As Long, json As String, items As Collection, item As Variant
    Dim pos As Long
    outTitle = "": outPrice = "": outPid = "": outErr = ""

    For start = 1 To API_MAX_START Step PAGE_SIZE
        If start > maxRank Then Exit For
        json = HttpGet(API_URL & "?query=" & UrlEncodeUtf8(keyword) & _
                       "&display=" & PAGE_SIZE & "&start=" & start & "&sort=sim", _
                       clientId, clientSecret, outErr)
        If outErr <> "" Then Exit Function

        Set items = ParseItems(json)
        If items.Count = 0 Then Exit Function

        pos = start
        For Each item In items
            If pos > maxRank Then Exit Function
            If IsMine(CStr(item(1)), CStr(item(2)), mallName, idList) Then
                outTitle = CStr(item(0))
                outPid = CStr(item(2))
                outPrice = CStr(item(3))
                FindRank = pos
                Exit Function
            End If
            pos = pos + 1
        Next item

        If items.Count < PAGE_SIZE Then Exit Function   ' 마지막 페이지
    Next start
End Function

Private Function IsMine(ByVal itemMall As String, ByVal itemPid As String, _
                        ByVal mallName As String, ByVal idList As Variant) As Boolean
    Dim i As Long
    If IsArray(idList) Then
        For i = LBound(idList) To UBound(idList)
            If idList(i) <> "" And idList(i) = itemPid Then IsMine = True: Exit Function
        Next i
    End If
    If mallName <> "" Then
        If StrComp(Replace(itemMall, " ", ""), Replace(mallName, " ", ""), vbTextCompare) = 0 Then IsMine = True
    End If
End Function

Private Function SplitIds(ByVal s As String) As Variant
    Dim parts As Variant, i As Long
    s = Replace(Replace(Replace(s, vbLf, ","), vbCr, ","), " ", "")
    If s = "" Then SplitIds = Empty: Exit Function
    parts = Split(s, ",")
    For i = LBound(parts) To UBound(parts)
        parts(i) = Trim$(parts(i))
    Next i
    SplitIds = parts
End Function

Private Function HttpGet(ByVal url As String, ByVal clientId As String, ByVal clientSecret As String, _
                         ByRef outErr As String) As String
    Dim http As Object
    On Error GoTo Fail
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.Open "GET", url, False
    http.setRequestHeader "X-Naver-Client-Id", clientId
    http.setRequestHeader "X-Naver-Client-Secret", clientSecret
    http.send
    If http.Status = 200 Then
        HttpGet = http.responseText
    ElseIf http.Status = 401 Then
        outErr = "API 인증 실패(401): Client ID/Secret 확인"
    ElseIf http.Status = 429 Then
        outErr = "API 호출 한도 초과(429): 잠시 후 다시 시도"
    Else
        outErr = "API 오류(" & http.Status & "): " & Left$(http.responseText, 200)
    End If
    Exit Function
Fail:
    outErr = "네트워크 오류: " & Err.Description
End Function

' 한글 키워드를 UTF-8 로 URL 인코딩
Private Function UrlEncodeUtf8(ByVal s As String) As String
    Dim stream As Object, bytes() As Byte, i As Long, b As Long, out As String
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2: stream.Charset = "utf-8": stream.Open
    stream.WriteText s
    stream.Position = 0: stream.Type = 1
    stream.Position = 3                     ' UTF-8 BOM 건너뛰기
    bytes = stream.Read
    stream.Close
    For i = LBound(bytes) To UBound(bytes)
        b = bytes(i)
        If (b >= 48 And b <= 57) Or (b >= 65 And b <= 90) Or (b >= 97 And b <= 122) _
           Or b = 45 Or b = 46 Or b = 95 Or b = 126 Then
            out = out & Chr$(b)
        Else
            out = out & "%" & Right$("0" & Hex$(b), 2)
        End If
    Next i
    UrlEncodeUtf8 = out
End Function

' 응답 JSON 의 items 배열을 파싱 -> 각 항목은 Array(title, mallName, productId, lprice)
Private Function ParseItems(ByVal json As String) As Collection
    Dim result As New Collection
    Dim p As Long, n As Long, ch As String, depth As Long
    Dim inString As Boolean, esc As Boolean, objStart As Long, obj As String

    p = InStr(1, json, """items""")
    If p = 0 Then Set ParseItems = result: Exit Function
    p = InStr(p, json, "[")
    If p = 0 Then Set ParseItems = result: Exit Function

    n = Len(json)
    For p = p + 1 To n
        ch = Mid$(json, p, 1)
        If inString Then
            If esc Then
                esc = False
            ElseIf ch = "\" Then
                esc = True
            ElseIf ch = """" Then
                inString = False
            End If
        Else
            Select Case ch
                Case """": inString = True
                Case "{"
                    If depth = 0 Then objStart = p
                    depth = depth + 1
                Case "}"
                    depth = depth - 1
                    If depth = 0 Then
                        obj = Mid$(json, objStart, p - objStart + 1)
                        result.Add Array(StripTags(JsonStr(obj, "title")), JsonStr(obj, "mallName"), _
                                         JsonStr(obj, "productId"), JsonStr(obj, "lprice"))
                    End If
                Case "]"
                    If depth = 0 Then Exit For
            End Select
        End If
    Next p
    Set ParseItems = result
End Function

' 평평한 JSON 객체에서 "key": "value" 문자열 값을 꺼낸다
Private Function JsonStr(ByVal obj As String, ByVal key As String) As String
    Dim p As Long, ch As String, out As String, n As Long
    p = InStr(1, obj, """" & key & """")
    If p = 0 Then Exit Function
    p = InStr(p + Len(key) + 2, obj, ":")
    If p = 0 Then Exit Function
    n = Len(obj)
    Do
        p = p + 1
        If p > n Then Exit Function
        ch = Mid$(obj, p, 1)
    Loop While ch = " " Or ch = vbTab Or ch = vbCr Or ch = vbLf

    If ch <> """" Then   ' 숫자 등 따옴표 없는 값
        Do While p <= n
            ch = Mid$(obj, p, 1)
            If ch = "," Or ch = "}" Or ch = " " Or ch = vbCr Or ch = vbLf Then Exit Do
            out = out & ch
            p = p + 1
        Loop
        JsonStr = out
        Exit Function
    End If

    For p = p + 1 To n
        ch = Mid$(obj, p, 1)
        If ch = """" Then Exit For
        If ch = "\" And p < n Then
            p = p + 1
            ch = Mid$(obj, p, 1)
            Select Case ch
                Case "n": out = out & vbLf
                Case "t": out = out & vbTab
                Case "r"
                Case "b", "f"
                Case "u"
                    out = out & ChrW$(CLng("&H" & Mid$(obj, p + 1, 4) & "&"))
                    p = p + 4
                Case Else: out = out & ch    ' \" \\ \/
            End Select
        Else
            out = out & ch
        End If
    Next p
    JsonStr = out
End Function

Private Function StripTags(ByVal s As String) As String
    s = Replace(s, "<b>", "")
    s = Replace(s, "</b>", "")
    s = Replace(s, "&amp;", "&")
    s = Replace(s, "&lt;", "<")
    s = Replace(s, "&gt;", ">")
    s = Replace(s, "&quot;", """")
    s = Replace(s, "&#39;", "'")
    StripTags = s
End Function
