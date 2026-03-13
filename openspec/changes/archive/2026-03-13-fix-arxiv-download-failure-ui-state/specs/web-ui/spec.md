## MODIFIED Requirements
### Requirement: ArXiv Download Progress Bar
鍓嶇 SHALL 鍦?Dashboard 椤甸潰鐨?Load Source 鎸夐挳涓嬫柟鏄剧ず涓嬭浇杩涘害鏉★紝鍙嶆槧鐪熷疄鐨勫悗绔笅杞借繘搴︺€?

#### Scenario: 鐐瑰嚮 Load Source 鍚庢樉绀鸿繘搴︽潯
- **WHEN** 鐢ㄦ埛鍦?arXiv ID 杈撳叆妗嗚緭鍏ユ湁鏁?ID 骞剁偣鍑?"Load Source" 鎸夐挳
- **THEN** 绯荤粺绔嬪嵆鍦ㄦ寜閽笅鏂规樉绀鸿繘搴︽潯缁勪欢
- **AND** 杩涘害鏉″垵濮嬪€间负 0%
- **AND** 鎸夐挳鐘舵€佸彉涓虹鐢?

#### Scenario: 杩涘害鏉″疄鏃舵洿鏂?
- **WHEN** 鍚庣杩斿洖涓嬭浇杩涘害鏇存柊锛堥€氳繃杞 /api/task/{task_id}锛?
- **THEN** 杩涘害鏉″钩婊戞洿鏂板埌鏈€鏂拌繘搴﹀€?
- **AND** 杩涘害鏉′笅鏂规樉绀哄綋鍓嶉樁娈垫弿杩帮紙濡?姝ｅ湪涓嬭浇 TeX 婧愮爜..."锛?

#### Scenario: 涓嬭浇瀹屾垚鍚庨殣钘忚繘搴︽潯
- **WHEN** 鍚庣杩斿洖 progress: 100 涓?status: "pending"
- **THEN** 杩涘害鏉℃秷澶?
- **AND** 鏄剧ず "Source Ready" 鎴愬姛鎻愮ず
- **AND** "Start Translation" 鎸夐挳鍙樹负鍙敤

#### Scenario: 涓嬭浇澶辫触鏃舵樉绀洪敊璇?
- **WHEN** 鍚庣杩斿洖 status: "failed"
- **THEN** 杩涘害鏉″彉涓虹孩鑹?閿欒鐘舵€?
- **AND** 鏄剧ず閿欒娑堟伅
- **AND** 鎻愪緵閲嶈瘯鎸夐挳

#### Scenario: SSE complete event with failed terminal status
- **WHEN** frontend receives SSE `complete` event
- **AND** event payload status is `failed`, `failed_compilation`, or `structure_invalid`
- **THEN** frontend MUST transition to failed download state
- **AND** frontend MUST NOT show success toast or `Source Ready`.
