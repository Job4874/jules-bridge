# Jules Bridge Quick Boot

The cockpit quick boot is repo-owned so the Desktop shortcut can be recreated
without hidden encoded shortcut logic.

## Files

- `Quick-Boot-Jules-Cockpit.ps1` boots the VM worker check, bridge/ngrok, Vite dashboard server, and browser.
- `Quick-Boot-Jules-Cockpit.cmd` is the double-click wrapper.
- `Install-Desktop-QuickBoot.ps1` creates or refreshes `Jules Bridge Quick Boot.lnk` on the Windows Desktop.
- `Open-Dashboard.cmd` and `Launch-Dashboard.ps1` delegate to the same launcher for compatibility.

## Install The Desktop Pin

Run from the repo root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install-Desktop-QuickBoot.ps1
```

The shortcut target is PowerShell with:

```powershell
-NoProfile -ExecutionPolicy Bypass -NoExit -File "<repo>\Quick-Boot-Jules-Cockpit.ps1"
```

## Verification

Use the bundled Codex runtime if `node`, `npm`, or `pnpm` are missing from the
regular Windows PATH:

```powershell
$env:PATH="C:\Users\abdul\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin;C:\Users\abdul\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin;$env:PATH"
pnpm --dir .\dashboard-ui run lint
pnpm --dir .\dashboard-ui run build
```

The stable dashboard URL is:

```text
http://127.0.0.1:5173/
```
