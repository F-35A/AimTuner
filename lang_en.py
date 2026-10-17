"""English UI text. Keys are the Korean source strings used with i18n.T()."""

EN = {
    "감도 ×{m:.3f} ({d})":
        "Sens ×{m:.3f} ({d})",
    "일치 — 이 감도로 확정":
        "Match — keep this sens",
    "올리기":
        "raise",
    "내리기":
        "lower",
    "{v:g}로 바꾸고 다시 측정 (예상 오차 {v2:+.1f}%)":
        "Set {v:g} and measure again (expected {v2:+.1f}%)",
    "일반":
        "Hip",
    "조준":
        "ADS",
    "낮추기 (지나침 많음)":
        "lower (overshooting)",
    "올리기 (덜 감 많음)":
        "raise (undershooting)",
    "{name}: {v:g} → {nv:g} {d}, 오버 {v2:.0f}%":
        "{name}: {v:g} → {nv:g} {d}, over {v2:.0f}%",
    "[{label}] 제외: ":
        "[{label}] skipped: ",
    "이미 쓸 수 있는 가장 높은 DPI입니다.":
        "Already the highest usable DPI.",
    "게임 창을 찾지 못했습니다. 게임 화면을 앞에 두고 누르세요.":
        "Game window not found. Bring the game to the front and press again.",
    "측정 실패. 무늬가 많은 벽/지형을 보고 다시 시도하세요.":
        "Measurement failed. Look at a textured wall/ground and try again.",
    "화면이 흔들려 측정이 불안정합니다. 움직이는 물체 없는 곳에서 다시.":
        "Screen too unstable. Try again where nothing is moving.",
    "일치 ({v:+.1f}%) — {v_cur:g} 확정":
        "Match ({v:+.1f}%) — {v_cur:g} final",
    "{v_cur:g} 확정 — 손감각 {v:+.1f}%, 이 칸 단위로는 이게 제일 가까움":
        "{v_cur:g} final — feel {v:+.1f}%, closest the step size allows",
    "{name}: 플릭 {n}개 — {MIN_FLICKS}개 이상 필요. 몇 판 더.":
        "{name}: {n} flicks — need {MIN_FLICKS}+. Play a few more.",
    "{name} {v:g} 확정 — 오버 {v2:.0f}% (적정 {v3:.0f}~{v4:.0f}%)":
        "{name} {v:g} final — over {v2:.0f}% (target {v3:.0f}~{v4:.0f}%)",
    "{name}: {v:g} → {nv:g} (일반 감도 변경분 보정)":
        "{name}: {v:g} → {nv:g} (compensating hip change)",
    "측정 3회 미만":
        "Fewer than 3 swipes",
    "측정 편차 {v:.1f}%":
        "Spread {v:.1f}%",
    "정지 떨림 {jitter:.1f}/s":
        "Rest jitter {jitter:.1f}/s",
    "{MAX_GOOD_DPI} 초과(스무딩 위험)":
        "Over {MAX_GOOD_DPI} (smoothing risk)",
    "측정 중 마우스가 움직였습니다. 손을 떼고 다시 누르세요.":
        "Mouse moved during the measurement. Let go and press again.",
    "화면이 단색/검정입니다. 무늬 있는 곳을 보거나 창 모드(테두리 없음)로 바꾸세요.":
        "Screen is flat/black. Look at something textured or use borderless window mode.",
    "감도가 너무 높아 1카운트도 화면 밖으로 나갑니다.":
        "Sens too high: even 1 count leaves the capture area.",
    "{name} {bv:g} 확정 — 칸 단위로는 이게 제일 균형 잡힘":
        "{name} {bv:g} final — best balance the step size allows",
    "{act}: '{spec}' 지원 안 하는 키":
        "{act}: '{spec}' is not a supported key",
    "문제없는 DPI 단계가 없습니다. 측정을 다시 해보세요.":
        "No usable DPI step. Measure again.",
    "화면 회전이 감지되지 않습니다. 1인칭으로, 마우스가 카메라를 돌리는 상태에서 누르세요.":
        "No camera rotation detected. Be in first person with the mouse turning the camera.",
    "화면 움직임이 일정하지 않습니다. 움직이는 물체 없는 곳에서 다시.":
        "Screen motion is inconsistent. Try again where nothing is moving.",
    "{tv:g}로 되돌리고 확정 — 손감각 {v:+.1f}%, 이 칸 단위로는 이게 제일 가까움":
        "Back to {tv:g} and final — feel {v:+.1f}%, closest the step size allows",
    "'{spec}' 중복 ({v}, {act})":
        "'{spec}' used twice ({v}, {act})",
    "큰 창 ↔ 작은 창":
        "Big window ↔ HUD",
    "일반 측정 / PVP 기록 시작·끝":
        "Hip measure / PVP record start·stop",
    "조준 측정":
        "ADS measure",
    "왼쪽 위":
        "Top left",
    "오른쪽 위":
        "Top right",
    "왼쪽 아래":
        "Bottom left",
    "오른쪽 아래":
        "Bottom right",
    "켜짐":
        "on",
    "꺼짐":
        "off",
    "윈도우 포인터 속도 {win_speed}/20 · 정확도 향상 {v}":
        "Windows pointer speed {win_speed}/20 · Enhance precision {v}",
    "기준 거리 (cm)":
        "Reference length (cm)",
    "게임 일반 감도 값":
        "Game hip sens",
    "조준 감도 값":
        "Game ADS sens",
    "감도 칸 단위":
        "Sens step",
    "최솟값":
        "Minimum",
    "지금 게임 일반 값":
        "Hip value now in game",
    "지금 게임 조준 값":
        "ADS value now in game",
    "일반 감도 (게임에 넣은 값)":
        "Hip sens (value in game)",
    "조준 감도":
        "ADS sens",
    "조준 감도는 일반 감도에 곱해지는 방식":
        "ADS sens is multiplied by hip sens",
    "게임 화면이 앞에 오면 작은 창으로 자동 전환":
        "Switch to HUD when the game is in front",
    "1  DPI 단계 측정":
        "1  Measure DPI steps",
    "2  게임에서 현재 감도":
        "2  Current sens in game",
    "3  새 감도 찾기":
        "3  Find new sens",
    "4  비교":
        "4  Compare",
    "어떻게 맞추나":
        "How it works",
    "낮은 DPI는 1카운트에 화면이 크게 돈다. 스코프에선 그 한 칸이 몇십 픽셀이라 그리드처럼 뚝뚝 끊긴다.":
        "At low DPI one mouse count turns the view a lot. Scoped in, that one step is dozens of pixels, so aim moves in a jerky grid.",
    "DPI를 올리고 게임 감도를 그만큼 내리면 손감각(마우스 1cm당 화면 이동)은 같고 한 칸만 작아진다.":
        "Raise DPI and lower game sens by the same ratio: same hand feel (screen travel per cm of mouse), smaller steps.",
    "게임 감도는 이 프로그램이 못 바꾼다. 대신 게임 안에서 {v}(일반)/{v2}(조준)을 누르면 화면이 실제로 얼마나 도는지 재서, 감도를 얼마나 올리고 내릴지 알려준다.":
        "This app can't change game sens. Instead press {v} (hip) / {v2} (ADS) in game: it measures how far the view really turns and tells you how much to raise or lower.",
    "자/카드(가로 8.56cm)를 마우스패드에 두고 기준 거리를 넣으세요. 대충이어도 단계 간 비율은 정확합니다.":
        "Put a ruler/card (8.56 cm wide) on the mousepad and enter its length. Even if rough, the ratio between steps stays exact.",
    "{label} 측정":
        "Measure {label}",
    "Esc: 취소":
        "Esc: cancel",
    "S: 확인 건너뛰기 · Esc: 뒤로":
        "S: skip check · Esc: back",
    "측정 결과":
        "Results",
    "{v} 기록 시작/끝 · {v2} 창 열기":
        "{v} record start/stop · {v2} open window",
    "{v} 일반 · {v2} 조준 · {v3} 창 열기":
        "{v} hip · {v2} ADS · {v3} open window",
    "4  전/후 비교":
        "4  Before / after",
    "전 (현재)":
        "Before",
    "후 (새 세팅)":
        "After",
    "차이":
        "Diff",
    "손감각이 같으니 금방 적응됩니다. 이제 PVP 몇 판으로 감도를 다듬으세요.":
        "Same hand feel, so you adapt fast. Now fine-tune with a few PVP rounds.",
    "5  PVP로 감도 다듬기":
        "5  Fine-tune with PVP",
    "플릭할 때 지나쳐서 되돌아오면(오버) 감도가 높은 것, 덜 가서 더 미는 일(언더)이 많으면 낮은 것. 우클릭 조준 중 플릭은 조준 감도로 따로 셉니다.":
        "Flick past and come back (over) = sens too high; stop short and push more (under) = too low. Flicks while holding right-click count toward ADS sens.",
    "세트 기록":
        "Sets",
    "{v}: 게임 안에서 기록 시작/끝 · 적정 오버 {v2:.0f}~{v3:.0f}%":
        "{v}: start/stop recording in game · target over {v2:.0f}~{v3:.0f}%",
    "설정":
        "Settings",
    "단축키 (게임 안에서도 작동, 키보드 조합키·마우스 옆버튼 MB4/MB5 가능)":
        "Hotkeys (work in game; combos and mouse side buttons MB4/MB5 allowed)",
    "작은 창 (게임 위 오버레이)":
        "HUD (overlay on the game)",
    "위치·불투명도는 클릭할 때마다 바뀝니다. 작은 창은 클릭이 통과돼서 게임 조작을 막지 않습니다. 다시 큰 창으로 오려면 단축키를 누르거나 이 프로그램으로 Alt+Tab.":
        "Click to cycle position and opacity. The HUD is click-through so it never blocks the game. To get the big window back press the hotkey or Alt+Tab to this app.",
    "기본 단축키로 되돌렸습니다":
        "Hotkeys reset to defaults",
    "+ DPI 단계 측정":
        "+ Measure DPI step",
    "마지막 단계 삭제":
        "Delete last step",
    "PVP 튜닝 →":
        "PVP tuning →",
    "게임에서 현재 감도 재기 →":
        "Measure current sens →",
    "단계":
        "Step",
    "실측 DPI":
        "Measured DPI",
    "편차":
        "Spread",
    "떨림":
        "Jitter",
    "상태":
        "Status",
    "마우스 DPI 버튼을 한 단계씩 돌리면서 단계마다 한 번씩 측정합니다. 지금 쓰는 단계도 포함해서 버튼이 지원하는 단계를 전부 재세요.":
        "Click through your mouse DPI button one step at a time and measure each. Include the step you use now — measure every step the button has.",
    "윈도우 설정이 바뀌어 기존 게임 측정은 지웠습니다. 다시 재세요.":
        "Windows settings changed, so old game measurements were cleared. Measure again.",
    "단계 {v}":
        "Step {v}",
    "마우스 DPI 버튼으로 잴 단계를 맞추세요.":
        "Set the DPI button to the step you want to measure.",
    "기준선({ref_cm:g}cm) 시작점 → 좌클릭 누른 채 끝점까지 → 떼기   [{v}/3]":
        "Start of the {ref_cm:g} cm line → hold left click to the end → release   [{v}/3]",
    "지금 쓰는 DPI 단계 확인":
        "Check current DPI step",
    "DPI 버튼은 평소 쓰는 그대로 두고, 기준선을 한 번 그어주세요.":
        "Leave the DPI button as you normally use it and swipe the line once.",
    "DPI 바꾸기":
        "Change DPI",
    "마우스 DPI 버튼을 [{label} · {dpi:,.0f}]로 바꾸고 기준선을 한 번 그어주세요.":
        "Set the DPI button to [{label} · {dpi:,.0f}] and swipe the line once.",
    "{cnt:,} 카운트 — 측정해 둔 단계와 맞는 게 없습니다. 다시 그어보세요.":
        "{cnt:,} counts — doesn't match any measured step. Swipe again.",
    "{cnt:,} 카운트 — 지금은 [{label}]입니다. 버튼을 바꾸고 다시.":
        "{cnt:,} counts — this is [{label}]. Change the button and swipe again.",
    "게임 일반 감도 값을 입력하세요 (지금 게임에 들어가 있는 숫자).":
        "Enter your game hip sens (the number in the game right now).",
    "쓸 수 있는 DPI 단계가 없습니다.":
        "No usable DPI step.",
    "{v} 측정 중… 마우스 손 떼기":
        "Measuring {v}… hands off the mouse",
    "← 현재 감도 다시":
        "← Measure current again",
    "DPI 다시 확인":
        "Re-check DPI",
    "게임 모드 (작은 창, {v})":
        "Game mode (HUD, {v})",
    "비교 보기 →":
        "Compare →",
    "2  게임에서 현재 감도 재기":
        "2  Measure current sens in game",
    "지금 DPI: {label} · {dpi:,.0f}   (게임 감도는 평소 그대로)":
        "DPI now: {label} · {dpi:,.0f}   (keep your usual game sens)",
    "아래에 지금 게임 감도 숫자를 넣고, 게임 감도 칸이 몇 단위로 움직이는지(0.01, 0.05 …) 적으세요.":
        "Enter your game sens below and how much one notch changes it (0.01, 0.05 …).",
    "게임 켜고 1인칭으로 무늬 있는 벽/지형을 보세요 (하늘·단색 X, 움직이는 사람 적은 곳).":
        "Start the game, first person, look at a textured wall/ground (no sky, few moving players).",
    "마우스에서 손 떼고 {v} → 일반 감도 측정. 프로그램이 마우스를 살짝 좌우로 움직여 화면 회전을 잽니다.":
        "Hands off the mouse, press {v} → hip measure. The app nudges the mouse left/right and measures the turn.",
    "우클릭 조준(ADS) 상태로 {v} → 조준 감도 측정.":
        "Hold right-click (ADS) and press {v} → ADS measure.",
    "{v}: 이 창 ↔ 게임 위 작은 창.":
        "{v}: this window ↔ HUD on the game.",
    "게임 칸 단위 {v:g}로 넣을 수 있는 조합 (클릭해서 바꾸기)":
        "Combos reachable with game step {v:g} (click to choose)",
    "DPI 버튼 → {label} ({dpi:,.0f}), 게임 일반 감도 → {v}. 1인칭에서 {v2}.":
        "DPI button → {label} ({dpi:,.0f}), game hip sens → {v}. In first person press {v2}.",
    "조준 감도는 일단 그대로 두고 조준한 채 {v}. 그대로 맞으면 조준 감도가 일반 감도에 곱해지는 방식입니다.":
        "Leave ADS sens as is, aim and press {v}. If it already matches, ADS is multiplied by hip sens.",
    "결과에 나온 값으로 바꾸고 다시 {v}/{v2} — '확정'이 뜰 때까지. 아래 칸 = 지금 게임에 넣은 값.":
        "Set the suggested value and press {v}/{v2} again until it says 'final'. Boxes below = values now in game.",
    "일반 {v}":
        "Hip {v}",
    "조준 {v}":
        "ADS {v}",
    "단축키 등록 실패 — 다른 프로그램이 같은 키를 쓰는 중. 설정에서 바꾸세요.":
        "Hotkey registration failed — another app uses that key. Change it in Settings.",
    "PVP 기록 중 {v}:{v2:02d}":
        "PVP recording {v}:{v2:02d}",
    "PVP 튜닝 · 기록 꺼짐":
        "PVP tuning · not recording",
    "현재 감도 재기":
        "Measuring current sens",
    "새 감도 찾기 · DPI {dpi:,.0f}":
        "Finding new sens · DPI {dpi:,.0f}",
    "마우스 DPI":
        "Mouse DPI",
    "완료. DPI 버튼은 [{label}]에 두고, 게임 감도는 위 값으로 쓰면 됩니다.":
        "Done. Keep the DPI button on [{label}] and use the game sens above.",
    "아직 '확정'이 안 나온 항목이 있습니다. 3단계에서 알려준 값으로 바꾸고 다시 재세요.":
        "Some items aren't 'final' yet. Set the values from step 3 and measure again.",
    "← 새 감도 찾기":
        "← Find new sens",
    "처음으로":
        "Start over",
    "PVP로 다듬기 →":
        "Fine-tune with PVP →",
    "← 처음":
        "← Start",
    "DPI 확인":
        "Check DPI",
    "기록 지우기":
        "Clear sets",
    "DPI 미측정":
        "DPI not measured",
    "기록 중 {v}:{v2:02d}":
        "Recording {v}:{v2:02d}",
    "조준 화면 — 기록 중":
        "Aiming — recording",
    "이번 세트 감도: 일반 {v} · 조준 {v2}":
        "This set: hip {v} · ADS {v2}",
    "사격 플릭":
        "Shot flicks",
    "오버% 일반/조준":
        "Over% hip/ADS",
    "아직 기록이 없습니다. 감도 넣고 '기록 시작' → PVP 2~3판 → '기록 끝'.":
        "No sets yet. Enter sens, 'Start recording' → 2–3 PVP rounds → 'Stop'.",
    "← 뒤로":
        "← Back",
    "단축키 기본값":
        "Default hotkeys",
    "작은 창 미리보기":
        "Preview HUD",
    "이 키는 쓸 수 없습니다. F키, 글자, 숫자, 넘패드, Insert/Home 등을 쓰세요.":
        "That key can't be used. Use F-keys, letters, digits, numpad, Insert/Home etc.",
    "너무 짧습니다. 기준선 끝까지 옮기세요.":
        "Too short. Move all the way to the end of the line.",
    "윈도우 포인터 1:1 적용":
        "Apply Windows pointer 1:1",
    "윈도우 포인터 OK":
        "Windows pointer OK",
    "  → 1:1(10, 끔) 권장. 게임 측정 전에 적용하세요.":
        "  → 1:1 (10, off) recommended. Apply before measuring in game.",
    "윈도우 포인터 1:1 적용됨":
        "Windows pointer set to 1:1",
    "적용 실패":
        "Failed to apply",
    "마우스에서 손 떼고 가만히":
        "Hands off the mouse, keep still",
    "정지 중 카운트 {still}":
        "Counts while still {still}",
    "실측 {dpi:,.0f} DPI":
        "Measured {dpi:,.0f} DPI",
    "편차 {v:.1f}% · 떨림 {jitter:.1f}/s":
        "Spread {v:.1f}% · jitter {jitter:.1f}/s",
    "Enter: 저장 · R: 다시 · Esc: 버리기":
        "Enter: save · R: redo · Esc: discard",
    "마우스 가속/스무딩 감지 — 게임 설정에서 꺼보세요.":
        "Mouse accel/smoothing detected — try turning it off in game.",
    "현재 세팅의 {name} 측정이 없어 비교할 수 없습니다.":
        "No {name} measurement of your current setup to compare with.",
    "한 칸 {pxpc:.2f}px → {pxpc2:.2f}px":
        "Step {pxpc:.2f}px → {pxpc2:.2f}px",
    "다음: 새 감도 찾기 →":
        "Next: find new sens →",
    "일반 감도":
        "Hip sens",
    "손감각 오차":
        "Feel error",
    "한 칸":
        "Step size",
    "마우스 소프트웨어로 DPI를 직접 넣을 수 있으면 {exact_dpi:,.0f}로 하면 오차 0%.":
        "If your mouse software takes an exact DPI, {exact_dpi:,.0f} gives 0% error.",
    "현재 한 칸 {pxpc:.2f}px":
        "Now step {pxpc:.2f}px",
    "현재: 미측정":
        "Now: not measured",
    "조준 중 — 기록":
        "Aiming — recording",
    "메뉴/다른 창 — 일시정지":
        "Menu / other window — paused",
    "{v} 감도 값 → {v2:g}":
        "{v} sens → {v2:g}",
    "{nm} 손감각 (px/cm)":
        "{nm} feel (px/cm)",
    "{nm} 한 칸 점프":
        "{nm} step jump",
    "{v:.1f}배 촘촘":
        "{v:.1f}× finer",
    "일반/조준 감도 값을 넣으세요 (게임에 들어간 숫자 그대로).":
        "Enter hip/ADS sens (exactly as in the game).",
    "기록 중 — Roblox 화면일 때만 기록. PVP 2~3판(오픈월드는 20~30분) 하고 {v}.":
        "Recording — only while Roblox is in front. Play 2–3 PVP rounds (open world 20–30 min), then {v}.",
    "플릭이 하나도 없습니다. Roblox 화면에서 실제로 플레이했는지 확인하세요.":
        "No flicks recorded. Make sure you actually played with Roblox in front.",
    "최종: 일반 {hv:g} · 조준 {av:g} · DPI {dpi:,.0f}":
        "Final: hip {hv:g} · ADS {av:g} · DPI {dpi:,.0f}",
    "게임에 위 값 넣고 다시 '기록 시작' → 2~3판.":
        "Put these values in the game and 'Start recording' again → 2–3 rounds.",
    "기록 끝 · 분석":
        "Stop · analyze",
    "기록 시작":
        "Start recording",
    "메뉴/지도/인벤 — 일시정지":
        "Menu/map/inventory — paused",
    "Roblox 화면 아님 — 일시정지":
        "Roblox not in front — paused",
    "키를 누르세요… (Esc 취소)":
        "Press a key… (Esc cancels)",
    "등록 실패 — 다른 프로그램이 사용 중":
        "Registration failed — key in use by another app",
    "위치":
        "Position",
    "불투명도":
        "Opacity",
    "문제 없음":
        "No problems",
    "오류: {ex}":
        "Error: {ex}",
    "{name} 기록: 한 칸 {pxpc:.2f}px":
        "{name} recorded: step {pxpc:.2f}px",
    "{v:.2f}배":
        "{v:.2f}×",
    "사격 {rec_shots} · {where}":
        "Shots {rec_shots} · {where}",
    "일반 {v} · 조준 {v2}":
        "Hip {v} · ADS {v2}",
    "{v} 일반 · {v2} 조준 측정":
        "{v} hip · {v2} ADS measure",
    "무료 배포 · 업데이트/문의: ":
        "Free · updates & support: ",
    "카운트 (긋는 중)":
        "counts (swiping)",
    "카운트":
        "counts",
    "마우스 입력 {hz:,.0f}Hz":
        "Mouse input {hz:,.0f} Hz",
    "  ← 이상함, 다시 그어보세요":
        "  ← looks wrong, swipe again",
    "{dpi:,.0f} DPI는 비정상입니다. 기준 거리(cm)를 확인하고 다시 그어보세요.":
        "{dpi:,.0f} DPI is not plausible. Check the reference length (cm) and swipe again.",
    "오른쪽으로 움직였습니다. 왼쪽으로 밀어주세요.":
        "You moved right. Move the mouse to the left.",
    "너무 짧습니다. 도착선까지 옮기세요.":
        "Too short. Move all the way to the finish mark.",
    "시작선":
        "Start",
    "도착선":
        "Finish",
    "마우스를 자의 시작점에 두고 클릭 (또는 Space) → 시작":
        "Put the mouse at the ruler's start mark and click (or Space) → start",
    "버튼 누르지 말고 왼쪽으로 밀기 → 도착점에서 클릭 (또는 Space)":
        "Don't hold any button — slide left → click at the finish mark (or Space)",
    "위아래로 많이 움직였습니다 — 자를 따라 수평으로":
        "Lots of up/down movement — keep it level along the ruler",
    "자 {ref_cm:g}cm · 오른쪽 시작점 → 왼쪽 도착점   [{v}/3]":
        "Ruler {ref_cm:g} cm · right start → left finish   [{v}/3]",
    "DPI 버튼은 평소 쓰는 그대로 두고, 자를 따라 한 번 재주세요.":
        "Leave the DPI button as you normally use it and measure along the ruler once.",
    "마우스 DPI 버튼을 [{label} · {dpi:,.0f}]로 바꾸고 자를 따라 한 번 재주세요.":
        "Set the DPI button to [{label} · {dpi:,.0f}] and measure along the ruler once.",
    "마우스를 자의 시작점(오른쪽 끝)에 두고 클릭 (또는 Space) → 시작":
        "Put the mouse at the ruler's start (right end) and click (or Space) → start",
    "버튼 누르지 말고 왼쪽으로 → 마우스가 실제 자 끝에 닿으면 클릭 (또는 Space)":
        "No buttons held — slide left → click when the mouse reaches the real ruler's end (or Space)",
    "화면은 움직임 확인용입니다. 멈추는 기준은 화면이 아니라 실제 자입니다.":
        "The screen only shows movement. Stop at the real ruler, not at anything on screen.",
    "모든 단계가 거의 같은 DPI로 나왔습니다. 단계마다 DPI 버튼을 바꿨는지, 실제 자 끝까지 밀었는지 확인하고 지운 뒤 다시 재세요.":
        "All steps came out at nearly the same DPI. Check that you changed the DPI button for each step and moved to the real ruler's end, then delete and measure again.",
    "1단계 DPI (마우스 스펙)":
        "Step 1 DPI (mouse spec)",
    "너무 짧습니다. 끝 지점까지 쭉 밀어주세요.":
        "Too short. Slide all the way to the end point.",
    "1단계와 비교해 비정상적인 값입니다. 같은 두 지점 사이를 밀었는지 확인하고 다시.":
        "Implausible compared with step 1. Make sure you moved between the same two points and try again.",
    "매번 같은 두 지점 사이 (예: 패드 오른쪽 끝 → 왼쪽 끝)   [{v}/3]":
        "Same two points every time (e.g. pad right edge → left edge)   [{v}/3]",
    "#{n}  {c:,} counts  (1단계 = {base:g} DPI 기준)":
        "#{n}  {c:,} counts  (step 1 = {base:g} DPI)",
    "자 필요 없음: 패드 끝↔끝처럼 손이 멈추는 고정된 두 지점 사이를 매번 똑같이 밀면 됩니다. 1단계 DPI만 스펙값을 넣으면 나머지는 비율로 계산됩니다.":
        "No ruler needed: slide between two fixed points where your hand stops (e.g. pad edge to edge), the same way each time. Enter only step 1's spec DPI; the rest come from the ratio.",
    "마우스를 시작 지점(예: 패드 오른쪽 끝)에 대고 클릭 (또는 Space) → 시작":
        "Put the mouse at the start point (e.g. pad right edge) and click (or Space) → start",
    "버튼 누르지 말고 왼쪽으로 → 끝 지점(예: 패드 왼쪽 끝)에 닿으면 클릭 (또는 Space)":
        "No buttons held — slide left → click when you reach the end point (e.g. pad left edge) (or Space)",
    "화면은 움직임 확인용입니다. 멈추는 기준은 화면이 아니라 손이 닿는 실제 지점입니다.":
        "The screen only shows movement. Stop at the real point your hand reaches, not at anything on screen.",
    "모든 단계가 거의 같게 나왔습니다. 단계마다 DPI 버튼을 바꿨는지 확인하세요. 바꿨는데도 같다면 이 마우스의 버튼은 센서 DPI가 아니라 윈도우 커서 속도만 바꾸는 방식이라 게임에는 효과가 없습니다.":
        "All steps came out nearly the same. Check you changed the DPI button for each. If you did, this mouse's button only changes the Windows cursor speed, not the sensor DPI, so it does nothing in games.",
    "버튼 누르지 말고 왼쪽으로 → 끝 지점에 닿아 멈추면 자동으로 끝":
        "No buttons held — slide left → it finishes by itself when you stop at the end point",
    "다시 켜면 적용됩니다":
        "Applies after restart",
}
