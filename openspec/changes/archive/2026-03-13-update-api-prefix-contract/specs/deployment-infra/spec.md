## MODIFIED Requirements
### Requirement: Fixed Backend Public URL
鍚庣 API SHALL 閫氳繃 Cloudflare Named Tunnel 鏆撮湶鍦ㄥ浐瀹氱殑鍏綉瀛愬煙鍚嶄笂锛屼笉鍥犻噸鍚€屽彉鍖栥€?

#### Scenario: Backend accessible via custom domain
- **WHEN** 澶栭儴璁惧璁块棶 `https://api.latextrans.online/api/health`
- **THEN** 杩斿洖鍋ュ悍妫€鏌?JSON 鍝嶅簲锛坰tatus=200锛?

#### Scenario: Tunnel restart preserves URL
- **WHEN** Named Tunnel 杩涚▼琚仠姝㈠苟閲嶆柊鍚姩
- **THEN** URL 涓嶅彉锛屾湇鍔′粛鍙甯歌闂?

### Requirement: Dynamic API URL Resolution
Frontend API calls SHALL use environment variable `VITE_API_BASE_URL` and MUST NOT hardcode localhost fallback.

#### Scenario: Production build has no hardcoded localhost fallback
- **WHEN** frontend is built in production mode
- **THEN** build artifacts MUST NOT contain `localhost:8000`

#### Scenario: Missing API base env fails fast
- **WHEN** `VITE_API_BASE_URL` is not set
- **THEN** frontend MUST throw an explicit configuration error
- **AND** frontend MUST block API request creation

#### Scenario: API requests append /api namespace
- **WHEN** frontend composes backend request URLs
- **THEN** request paths SHALL be formed as `${VITE_API_BASE_URL}/api/...`
- **AND** callers MUST NOT bypass this contract with non-prefixed paths such as `/history`.
