# Browser Automation Memory

Learnings from browser tasks.

## TASK-001 — 2026-07-15T21:13:08.621027+00:00
- **Type**: quiz
- **URL**: https://docs.google.com/forms/d/e/1FAIpQLSdummy/viewform
- **Outcome**: failure
- **Lesson**: Quiz at https://docs.google.com/forms/d/e/1FAIpQLSdummy/viewform FAILED: BrowserType.launch_persistent_context: Failed to create a ProcessSingleton for your profile directory. This usually means that the profile is already in use by another instance of Chromium.
Call log:
  - <launching> C:\Users\shpctac1002c\AppData\Local\Google\Chrome\Application\chrome.exe --disable-field-trial-config --disable-background-networking --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-back-forward-cache --disable-breakpad --disable-client-side-phishing-detection --disable-component-extensions-with-background-pages --disable-component-update --no-default-browser-check --disable-default-apps --disable-dev-shm-usage --disable-edgeupdater --disable-extensions --disable-features=AvoidUnnecessaryBeforeUnloadCheckSync,BoundaryEventDispatchTracksNodeRemoval,DestroyProfileOnBrowserClose,DialMediaRouteProvider,GlobalMediaControls,HttpsUpgrades,LensOverlay,MediaRouter,PaintHolding,ThirdPartyStoragePartitioning,Translate,AutoDeElevate,RenderDocument,OptimizationHints,msForceBrowserSignIn,msEdgeUpdateLaunchServicesPreferredVersion --enable-features=CDPScreenshotNewSurface --allow-pre-commit-input --disable-hang-monitor --disable-ipc-flooding-protection --disable-popup-blocking --disable-prompt-on-repost --disable-renderer-backgrounding --force-color-profile=srgb --metrics-recording-only --no-first-run --password-store=basic --use-mock-keychain --no-service-autorun --export-tagged-pdf --disable-search-engine-choice-screen --unsafely-disable-devtools-self-xss-warnings --edge-skip-compat-layer-relaunch --disable-infobars --disable-search-engine-choice-screen --disable-sync --enable-unsafe-swiftshader --no-sandbox --disable-blink-features=AutomationControlled --no-first-run --no-default-browser-check --user-data-dir=C:\Users\shpctac1002c\AppData\Local\Google\Chrome\User Data --remote-debugging-pipe about:blank
  - <launched> pid=2336
  - [pid=2336][err] [2336:8600:0715/151308.331:ERROR:chrome\browser\process_singleton_win.cc:410] Lock file can not be created! Error code: 32
  - [pid=2336][err] [2336:8600:0715/151308.331:ERROR:chrome\app\chrome_main_delegate.cc:520] Failed to create a ProcessSingleton for your profile directory. This means that running multiple instances would start multiple browser processes rather than opening a new window in the existing process. Aborting now to avoid profile corruption.
  - [pid=2336] <gracefully close start>
  - [pid=2336] <kill>
  - [pid=2336] <will force kill>
  - [pid=2336] taskkill stderr: ERROR: The process "2336" not found.
  - [pid=2336] <process did exit: exitCode=21, signal=null>
  - [pid=2336] starting temporary directories cleanup
  - [pid=2336] finished temporary directories cleanup
  - [pid=2336] <gracefully close end>
. Check: 1) URL accessible? 2) Chrome profile has auth? 3) DOM selectors changed?


## TASK-002 — 2026-07-15T21:13:20.320743+00:00
- **Type**: research
- **URL**: https://www.reuters.com/business/finance/
- **Outcome**: failure
- **Lesson**: Research task TASK-002 at https://www.reuters.com/business/finance/ — failed: BrowserType.launch_persistent_context: Failed to create a ProcessSingleton for your profile directory. This usually means that the profile is already in use by another instance of Chromium.
Call log:
  - <launching> C:\Users\shpctac1002c\AppData\Local\Google\Chrome\Application\chrome.exe --disable-field-trial-config --disable-background-networking --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-back-forward-cache --disable-breakpad --disable-client-side-phishing-detection --disable-component-extensions-with-background-pages --disable-component-update --no-default-browser-check --disable-default-apps --disable-dev-shm-usage --disable-edgeupdater --disable-extensions --disable-features=AvoidUnnecessaryBeforeUnloadCheckSync,BoundaryEventDispatchTracksNodeRemoval,DestroyProfileOnBrowserClose,DialMediaRouteProvider,GlobalMediaControls,HttpsUpgrades,LensOverlay,MediaRouter,PaintHolding,ThirdPartyStoragePartitioning,Translate,AutoDeElevate,RenderDocument,OptimizationHints,msForceBrowserSignIn,msEdgeUpdateLaunchServicesPreferredVersion --enable-features=CDPScreenshotNewSurface --allow-pre-commit-input --disable-hang-monitor --disable-ipc-flooding-protection --disable-popup-blocking --disable-prompt-on-repost --disable-renderer-backgrounding --force-color-profile=srgb --metrics-recording-only --no-first-run --password-store=basic --use-mock-keychain --no-service-autorun --export-tagged-pdf --disable-search-engine-choice-screen --unsafely-disable-devtools-self-xss-warnings --edge-skip-compat-layer-relaunch --disable-infobars --disable-search-engine-choice-screen --disable-sync --enable-unsafe-swiftshader --no-sandbox --disable-blink-features=AutomationControlled --no-first-run --no-default-browser-check --user-data-dir=C:\Users\shpctac1002c\AppData\Local\Google\Chrome\User Data --remote-debugging-pipe about:blank
  - <launched> pid=14728
  - [pid=14728][err] [14728:11752:0715/151320.010:ERROR:chrome\browser\process_singleton_win.cc:410] Lock file can not be created! Error code: 32
  - [pid=14728][err] [14728:11752:0715/151320.010:ERROR:chrome\app\chrome_main_delegate.cc:520] Failed to create a ProcessSingleton for your profile directory. This means that running multiple instances would start multiple browser processes rather than opening a new window in the existing process. Aborting now to avoid profile corruption.
  - [pid=14728] <gracefully close start>
  - [pid=14728] <kill>
  - [pid=14728] <will force kill>
  - [pid=14728] taskkill stderr: ERROR: The process "14728" not found.
  - [pid=14728] <process did exit: exitCode=21, signal=null>
  - [pid=14728] starting temporary directories cleanup
  - [pid=14728] finished temporary directories cleanup
  - [pid=14728] <gracefully close end>


