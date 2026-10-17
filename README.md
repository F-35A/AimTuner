# AimTuner

Free, open-source DPI & sensitivity tuner for Roblox FPS games (BRM5 etc.).
무료 오픈소스 DPI·감도 세팅기 (BRM5 등 Roblox FPS).

**다운로드 / Download:** [Releases](../../releases/latest) → `AimTuner-vX.Y.Z-windows.zip` → 압축 풀고 `AimTuner.exe`

**배포 / Distributed via:** Discord — https://discord.gg/gfRYA7AqkR
(업데이트·버그 제보·문의 / updates, bug reports, support)

> 처음 실행 시 "Windows의 PC 보호" 창이 뜨면 **추가 정보 → 실행**. 서명 안 된 무료 프로그램이라 뜨는 경고입니다. 일부 백신이 PyInstaller EXE를 오탐할 수 있습니다 — 걱정되면 소스에서 직접 빌드하세요.
> On first run, if "Windows protected your PC" appears, click **More info → Run anyway** (unsigned free app). Some antivirus tools flag PyInstaller EXEs by mistake — build from source if unsure.

## English

1. **Measure DPI steps** – no ruler needed. For each DPI button step: click at a fixed start
   point (e.g. pad right edge), slide left without holding to a fixed end point (e.g.
   pad left edge) — it finishes by itself when your hand stops. 3 times. Enter only step 1's spec DPI; the rest come from the ratio. Bad
   steps (jitter, spread, >3200) are flagged; identical steps mean the button doesn't change
   the sensor DPI.
2. **Measure current sens in game** (optional) – enter your hip/ADS sens and the in-game step
   (e.g. 0.01). Press **F7** (hip) or **F8** while aiming (ADS). The app nudges the mouse and
   measures how far the view turns.
3. **Find new sens** – it lists DPI + sens combos you can actually type into the game and
   guides you, measurement by measurement, to the same hand feel at a higher DPI.
4. **Fine-tune with PVP** – press **F7** in game to record, play 2–3 rounds (open world
   20–30 min), press **F7** again. Flicks that end in a shot are analysed: coming back after a
   flick = overshoot (sens too high), pushing further = undershoot (too low). Hip and ADS
   (right-click held) are tuned separately until both say *final*.

- **F6** switches between the big window and a click-through HUD. All keys can be changed in
  Settings (combos and mouse side buttons MB4/MB5 work).
- Game files are never touched. Only the Windows pointer setting changes, when you press its
  button.
- PVP recording only *reads* your mouse. The F7/F8 measurement in steps 2–3 *moves* the mouse
  like a macro tool would; use it at your own risk on games with anti-cheat.
- The game must run windowed/borderless for F7/F8 (screen capture).

## 한국어

1. **DPI 단계 측정** – 자 필요 없음. 단계마다: 고정된 시작점(예: 패드 오른쪽 끝)에서 클릭 → 버튼 안 누르고 왼쪽으로 → 고정된 끝점에서 멈추면 자동으로 끝, 3번. 1단계 스펙 DPI만 입력하면 나머지는 비율로 계산.
2. **게임에서 현재 감도** (선택) – 일반/조준 감도와 칸 단위 입력 → **F7**(일반), 조준한 채 **F8**.
3. **새 감도 찾기** – 실제로 넣을 수 있는 DPI+감도 조합 중 최적을 찾아 단계별 안내.
4. **PVP로 다듬기** – 게임 안에서 **F7**로 기록 시작, 2~3판(오픈월드 20~30분), **F7**로 끝.
   쏜 플릭만 분석해서 오버/언더 비율로 일반·조준 감도를 각각 "확정"까지 조정.

- **F6** 큰 창 ↔ 게임 위 작은 창. 단축키는 설정에서 변경 (조합키, 마우스 옆버튼 가능).
- 게임 파일은 건드리지 않음. 윈도우 포인터 설정만 버튼 누를 때 변경.
- PVP 기록은 마우스를 *읽기만* 함. 2~3단계 F7/F8 측정은 매크로처럼 마우스를 *움직임* — 안티치트 있는 게임에선 본인 책임.
- F7/F8 측정은 게임이 창/테두리 없는 창 모드여야 함.

## Release / 배포

`v*` 태그를 푸시하면 GitHub Actions가 Windows에서 테스트 → EXE 빌드 → Release에 zip 첨부까지 자동으로 합니다.
Pushing a `v*` tag makes GitHub Actions test, build the EXE on Windows and attach the zip to a Release.

```
git tag v1.0.4 && git push origin v1.0.4
```

## Build / 빌드

```
pip install pygame numpy pyinstaller
pyinstaller --onefile --windowed --name AimTuner --icon icon.ico --add-data "icon.png;." --exclude-module fakeplat app.py
```
Tests: `pip install pytest && pytest tests`

License: MIT (see LICENSE, THIRD_PARTY_NOTICES.txt)
