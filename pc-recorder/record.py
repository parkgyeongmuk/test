# 쇼츠 컷 자동 녹화 (Windows 11 + OBS + 크롬)
# 매일 아침 GitHub의 clips/latest.json(그날 대본의 컷 목록)을 받아서,
# 컷마다 크롬으로 영상을 그 초로 옮기고 OBS로 녹화해 저장 폴더\날짜\채널\ 에 저장한다.
#
# 사용법:
#   python record.py --dry-run   오늘 컷 목록만 보여주고 녹화는 안 함
#   python record.py --test      첫 영상의 첫 컷 하나만 녹화 (설정 확인용, 날짜 확인 안 함)
#   python record.py             전체 녹화 (작업 스케줄러가 매일 실행)
#   python record.py --login     녹화 전용 크롬을 열어 YouTube에 한 번 로그인 (창을 닫으면 끝)
import argparse, datetime as dt, json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
LOG = HERE / "record.log"

# 녹화에 방해되는 플레이어 UI(재생바, 제목, 자막, 추천 영상, 마우스 커서)를 CSS로 숨긴다.
HIDE_CSS = """
.ytp-chrome-bottom, .ytp-chrome-top, .ytp-gradient-bottom, .ytp-gradient-top,
.ytp-caption-window-container, .ytp-ce-element, .ytp-paid-content-overlay,
.ytp-pause-overlay, .ytp-spinner, .ytp-bezel-text-wrapper, .ytp-bezel,
.ytp-cards-teaser, .ytp-iv-player-content, .iv-branding, .ytp-autonav-endscreen-countdown-overlay
{ display: none !important; opacity: 0 !important; }
* { cursor: none !important; }
"""
SKIP_BUTTONS = ".ytp-skip-ad-button, .ytp-ad-skip-button, .ytp-ad-skip-button-modern, .ytp-ad-skip-button-container button, .ytp-skip-ad button"


def log(msg):
    line = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sec(ts):
    """'29:07' 또는 '1:12:05' → 초"""
    p = [float(x) for x in str(ts).split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def safe(name):
    """윈도우 폴더/파일 이름에 못 쓰는 문자를 뺀다."""
    return re.sub(r'[\\/:*?"<>|]+', "", name).strip().rstrip(".") or "이름없음"


def fetch_clips():
    url = f"https://api.github.com/repos/{CFG['repo']}/contents/{CFG['clips_path']}?ref={CFG['branch']}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CFG['github_token']}",
                                               "Accept": "application/vnd.github.raw", "User-Agent": "shorts-recorder"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))


def connect_obs():
    """OBS가 꺼져 있으면 켜고, WebSocket에 연결한다."""
    import obsws_python as obs
    def conn():
        return obs.ReqClient(host=CFG.get("obs_host", "localhost"), port=CFG.get("obs_port", 4455),
                             password=CFG["obs_password"], timeout=5)
    try:
        return conn()
    except Exception as e:
        if "identify" in str(e):  # OBS는 켜져 있는데 비밀번호가 다를 때
            raise RuntimeError("OBS 비밀번호가 맞지 않아요. OBS의 도구 → WebSocket 서버 설정 → 연결 정보 표시에서 "
                               "비밀번호를 다시 복사해 config.json의 obs_password에 넣어 주세요.")
        exe = Path(CFG["obs_exe"])
        log("OBS 실행 중...")
        subprocess.Popen([str(exe), "--minimize-to-tray", "--disable-shutdown-check"], cwd=str(exe.parent))
        for _ in range(30):
            time.sleep(2)
            try:
                return conn()
            except Exception as e:
                if "identify" in str(e):
                    raise RuntimeError("OBS 비밀번호가 맞지 않아요. config.json의 obs_password를 확인해 주세요.")
    raise RuntimeError("OBS WebSocket에 연결할 수 없어요. OBS의 도구 → WebSocket 서버 설정을 확인해 주세요.")


def close_recording_chrome(profile):
    """녹화 전용 프로필로 켜져 있는 크롬(예: --login 창, 지난번에 남은 창)을 끈다.
    같은 프로필 크롬이 이미 떠 있으면 새 크롬이 그 창으로 넘어가 버려서 자동 조작이 안 된다.
    평소 쓰는 크롬(다른 프로필)은 건드리지 않는다."""
    ps = ("Get-CimInstance Win32_Process -Filter \"name='chrome.exe'\" | "
          f"Where-Object {{ $_.CommandLine -like '*{profile}*' }} | "
          "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $_.ProcessId }")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=30).stdout.split()
    except Exception as e:
        log(f"  남은 크롬 확인 실패: {e}")
        return
    if out:
        log(f"  남아 있던 녹화 전용 크롬 {len(out)}개를 종료했어요")
        time.sleep(3)
    lock = profile / "lockfile"
    try:
        if lock.exists(): lock.unlink()
    except OSError:
        raise RuntimeError("녹화 전용 크롬이 아직 켜져 있어요. 크롬 창을 모두 닫고 다시 실행해 주세요.")


class Player:
    """크롬(Playwright)으로 YouTube 플레이어를 조작한다."""

    def __init__(self, pw):
        profile = HERE / "chrome-profile"
        close_recording_chrome(profile)
        log("크롬 여는 중...")
        self.ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(HERE / "chrome-profile"), channel="chrome", headless=False, no_viewport=True,
            ignore_default_args=["--enable-automation"],
            args=["--start-fullscreen", "--autoplay-policy=no-user-gesture-required", "--disable-infobars"])
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()

    def js(self, code):
        return self.page.evaluate(f"() => {{ const p = document.querySelector('#movie_player'); {code} }}")

    def ad_showing(self):
        return bool(self.js("return p && p.classList.contains('ad-showing');"))

    def wait_ads(self, limit=180):
        """광고가 나오면 건너뛰기 버튼을 누르거나 끝날 때까지 기다린다."""
        t0 = time.time()
        while self.ad_showing() and time.time() - t0 < limit:
            btn = self.page.query_selector(SKIP_BUTTONS)
            if btn and btn.is_visible():
                try:
                    btn.click(timeout=2000)
                    log("  광고 건너뛰기")
                except Exception:
                    pass
            time.sleep(1)
        if self.ad_showing():
            raise RuntimeError("광고가 너무 길어요")

    def open(self, vid):
        log(f"  영상 여는 중: https://www.youtube.com/watch?v={vid}")
        self.page.goto(f"https://www.youtube.com/watch?v={vid}", wait_until="domcontentloaded", timeout=60000)
        try:
            self.page.wait_for_selector("#movie_player video", timeout=60000)
        except Exception:
            if "로그인" in self.page.content() or "Sign in" in self.page.content():
                raise RuntimeError("YouTube가 로그인을 요구해요. python record.py --login 으로 한 번 로그인해 주세요.")
            raise
        log("  영상 페이지 열림, 광고 확인 중...")
        time.sleep(3)
        self.wait_ads()
        # 소리 켜기, 1080p 시도, 자막 끄기
        self.js("p.unMute(); p.setVolume(100); try { p.setPlaybackQualityRange('hd1080','hd1080'); } catch(e) {}"
                "try { p.unloadModule('captions'); } catch(e) {}")
        self.fullscreen()
        self.page.add_style_tag(content=HIDE_CSS)
        self.page.mouse.move(5, 5)

    def fullscreen(self):
        if self.page.evaluate("() => !!document.fullscreenElement"):
            return
        self.page.bring_to_front()
        self.page.keyboard.press("f")
        time.sleep(1.5)
        if not self.page.evaluate("() => !!document.fullscreenElement"):
            try:
                self.page.click(".ytp-fullscreen-button", timeout=3000)
                time.sleep(1.5)
            except Exception:
                log("  전체화면 전환 실패 (창 모드로 녹화)")

    def now(self):
        return float(self.js("return p.getCurrentTime();") or 0)

    def reach(self, t, lead=8):
        """t초 직전에 광고 없이 '재생 중'인 상태를 만든다.
        컷 위치로 바로 건너뛰면 그때마다 광고가 새로 끼기 쉬워서, lead초 앞으로 한 번만 이동해 틀어 두고
        광고가 나오면 넘긴 뒤 자연스럽게 재생되다가 t에 닿는 순간 True를 돌려준다(멈추지 않은 채로)."""
        for _ in range(6):
            self.js(f"p.seekTo({max(0, t - lead)}, true); p.playVideo();")
            t0 = time.time()
            while time.time() - t0 < lead + 40:
                time.sleep(0.2)
                if self.ad_showing():
                    self.wait_ads()  # 광고가 끝나면 원래 위치부터 이어서 재생된다
                    self.js("p.playVideo();")
                    continue
                cur = self.now()
                if t - 0.3 <= cur <= t + 1.0:
                    return True
                if cur > t + 1.0 or cur < t - lead - 30:  # 위치가 엉뚱해지면 다시 이동
                    break
        return False

    def close(self):
        self.ctx.close()


def record_cut(player, cl, vid, cut, out_dir, idx):
    pad_b, pad_a = CFG.get("pad_before", 1.5), CFG.get("pad_after", 1.5)
    start, end = max(0, sec(cut["start"]) - pad_b), sec(cut["end"]) + pad_a
    stem = f"{idx:02d}_{safe(cut['name'])}"
    if any(out_dir.glob(stem + ".*")):
        log(f"  이미 있음: {stem}")
        return True
    for attempt in range(1, 6):
        if not player.reach(start):
            log(f"  컷 위치로 가지 못함, 다시 시도 ({attempt}/5)")
            continue
        cl.start_record()  # 이미 재생 중인 상태에서 바로 녹화 시작
        t0, broken = time.time(), False
        while time.time() - t0 < end - start:
            time.sleep(0.3)
            if player.ad_showing():  # 녹화 중에 광고가 끼면 이번 녹화는 버리고 다시
                broken = True
                break
        path = Path(cl.stop_record().output_path)
        player.js("p.pauseVideo();")
        target = out_dir / (stem + path.suffix)  # OBS 녹화 형식(mp4/mkv) 그대로
        for _ in range(20):  # OBS가 파일을 다 쓸 때까지 잠깐 기다린다
            time.sleep(0.5)
            try:
                if broken:
                    path.unlink()
                else:
                    os.replace(path, target)
                break
            except PermissionError:
                continue
        if not broken:
            log(f"  저장: {target.name} ({cut['start']}~{cut['end']})")
            return True
        log(f"  녹화 중 광고 발생, 다시 시도 ({attempt}/5)")
        player.wait_ads()
    log(f"  실패: {cut['name']}")
    return False


def chrome_login():
    """녹화 전용 크롬 프로필을 평소 크롬처럼 열어서 직접 YouTube에 로그인하게 한다.
    (자동 조작 중인 크롬에서는 구글 로그인이 막혀서, 로그인만 일반 크롬으로 한다)"""
    cands = [Path(os.environ.get(k, "")) / "Google/Chrome/Application/chrome.exe"
             for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
    exe = next((c for c in cands if c.is_file()), None)
    if not exe:
        raise RuntimeError("chrome.exe를 찾지 못했어요. 크롬이 설치되어 있는지 확인해 주세요.")
    close_recording_chrome(HERE / "chrome-profile")
    log("녹화 전용 크롬을 엽니다. YouTube에 로그인한 뒤 크롬 창을 닫아 주세요.")
    subprocess.run([str(exe), f"--user-data-dir={HERE / 'chrome-profile'}", "https://accounts.google.com/ServiceLogin?continue=https://www.youtube.com/"])
    time.sleep(2)
    close_recording_chrome(HERE / "chrome-profile")  # 창을 닫아도 뒤에 남는 크롬까지 정리
    log("로그인 창을 닫았어요. 이제 python record.py --test 로 다시 시험해 보세요.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--login", action="store_true")
    a = ap.parse_args()
    if a.login:
        return chrome_login()

    data = fetch_clips()
    today = dt.date.today().isoformat()
    log(f"컷 목록 날짜 {data.get('date')} (오늘 {today}), 영상 {len(data.get('videos', []))}개")
    if data.get("date") != today and not (a.test or a.dry_run):
        log("오늘 컷 목록이 아직 없어요. 아침 메일 작업이 실패했을 수 있어요. 종료합니다.")
        return
    videos = data["videos"][:1] if a.test else data["videos"]
    if a.test:
        videos[0] = dict(videos[0], cuts=videos[0]["cuts"][:1])
    if a.dry_run:
        for v in videos:
            print(f"- {v['channel']} | {v['title']} ({v['video_id']})")
            for c in v["cuts"]:
                print(f"    {c['name']}: {c['start']}~{c['end']}")
        return

    from playwright.sync_api import sync_playwright
    root = Path(CFG["save_dir"]) / data.get("date", today)
    cl = connect_obs()
    log("OBS 연결 완료")
    ok = total = 0
    with sync_playwright() as pw:
        player = Player(pw)
        try:
            for v in videos:
                out_dir = root / safe(v["channel"])
                out_dir.mkdir(parents=True, exist_ok=True)
                if v.get("script"):
                    (out_dir / "대본.txt").write_text(f"{v['title']}\n{v.get('url', '')}\n\n{v['script']}", encoding="utf-8")
                log(f"{v['channel']} | {v['title']}")
                try:
                    player.open(v["video_id"])
                    for i, cut in enumerate(v["cuts"], 1):
                        total += 1
                        ok += record_cut(player, cl, v["video_id"], cut, out_dir, i)
                except Exception as e:
                    log(f"  영상 건너뜀: {e}")
        finally:
            player.close()
    log(f"완료: {ok}/{total}개 컷 저장 → {root}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"오류: {e}")
        sys.exit(1)
