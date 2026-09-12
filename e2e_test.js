const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = '/Users/macmolt/.gemini/antigravity-ide/brain/e5c83a1e-6721-485a-914a-beb5074b3ae9';
const CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const TARGET_URL = 'http://localhost:3002';

async function runE2ETest() {
  console.log('==============================================');
  console.log('🚀 AI DevEnv Quest 200점 달성 E2E 테스트 시작');
  console.log('   Target URL:', TARGET_URL);
  console.log('   Chrome Path:', CHROME_PATH);
  console.log('==============================================\n');

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900 });

  const testResults = [];
  function assert(title, condition, extra = '') {
    if (condition) {
      console.log(`✅ [PASS] ${title} ${extra}`);
      testResults.push({ title, pass: true, extra });
    } else {
      console.error(`❌ [FAIL] ${title} ${extra}`);
      testResults.push({ title, pass: false, extra });
    }
  }

  try {
    // 1. 페이지 로드
    console.log('[1/7] 웹페이지 로드 중...');
    const response = await page.goto(TARGET_URL, { waitUntil: 'networkidle0', timeout: 15000 });
    assert('HTTP 상태 코드 200 응답', response.status() === 200, `Status: ${response.status()}`);

    const title = await page.title();
    assert('페이지 타이틀 확인', title.includes('200점 도전'), `Title: ${title}`);

    // 2. 서버 연결 상태 확인
    console.log('[2/7] 검증 서버 연결(Ping) 상태 확인...');
    await page.waitForFunction(() => {
      const dot = document.getElementById('sb-sdot');
      return dot && dot.classList.contains('live');
    }, { timeout: 6000 });
    assert('검증 서버 라이브 인디케이터(초록 점) 활성화', true);

    // 3. OS 전환 토글 테스트
    console.log('[3/7] OS 토글 옵션(Windows / macOS) 테스트...');
    const isMacBtnPresent = await page.$('#btn-os-mac') !== null;
    assert('상단 macOS 선택 버튼 존재', isMacBtnPresent);

    await page.click('#btn-os-mac');
    await new Promise(r => setTimeout(r, 400));

    const bodyClass = await page.evaluate(() => document.body.className);
    assert('macOS 모드 클래스 적용', bodyClass.includes('os-mac'), `Body class: ${bodyClass}`);

    const modKeyText = await page.$eval('.key-mod', el => el.textContent);
    assert('단축키 Cmd ⌘ 동적 전환 확인', modKeyText.includes('Cmd'), `Key text: ${modKeyText}`);

    // 4. 초기 점수 확인
    const initialScore = await page.$eval('#sb-num', el => parseInt(el.textContent, 10));
    console.log(`[4/7] 점수 시스템 확인 (초기 점수: ${initialScore}점)`);

    // 5. 전체 환경 자동 점검 버튼 클릭 (Step 10)
    console.log('[5/7] ⚡ 전체 환경 자동 점검 버튼 클릭...');
    const verifyAllBtn = await page.$('#verify-all-btn');
    assert('전체 자동 점검 버튼 존재', verifyAllBtn !== null);

    await page.click('#verify-all-btn');

    // 점검 완료 대기
    console.log('     점검 요청 처리 대기 중...');
    await page.waitForFunction(() => {
      const btn = document.getElementById('verify-all-btn');
      return btn && (btn.classList.contains('ok') || btn.classList.contains('fail'));
    }, { timeout: 25000 });

    const btnStatus = await page.$eval('#verify-all-btn', el => ({
      text: el.textContent,
      className: el.className
    }));
    assert('전체 점검 버튼 성공 완료', btnStatus.className.includes('ok'), `Btn text: "${btnStatus.text}"`);

    // 6. 200점 만점 및 마스터 달성 검증
    console.log('[6/7] 200점 만점 및 마스터 등급 검증...');
    // 숫자 애니메이션 완료 대기 (500ms + 여유)
    await new Promise(r => setTimeout(r, 1200));

    const finalScore = await page.$eval('#sb-num', el => parseInt(el.textContent, 10));
    assert('최종 점수 200점 만점 달성', finalScore === 200, `Score: ${finalScore} / 200`);

    const levelText = await page.$eval('#sb-lv', el => el.textContent.trim());
    assert('최종 레벨 "🏆 마스터!" 달성', levelText.includes('마스터'), `Level: ${levelText}`);

    const allBannerVisible = await page.$eval('#sb-all', el => !el.hidden && el.offsetWidth > 0);
    assert('🏆 전체 완료 축하 배너 노출', allBannerVisible);

    // 각 단계별 10개 항목 모두 체크 완료되었는지 확인
    const checklistStatus = await page.$$eval('.sb-li', items => {
      return items.map(li => ({
        id: li.dataset.id,
        done: li.classList.contains('done'),
        check: li.querySelector('.sb-ck').textContent.trim()
      }));
    });
    const allDone = checklistStatus.every(item => item.done && item.check === '✅');
    assert('10단계 모든 퀘스트 완료(✅)', allDone, `완료 항목수: ${checklistStatus.filter(x=>x.done).length}/10`);

    // 7. 스크린샷 캡처 및 아티팩트 저장
    console.log('[7/7] 결과 스크린샷 저장 중...');
    if (!fs.existsSync(ARTIFACT_DIR)) {
      fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
    }
    const fullScreenshotPath = path.join(ARTIFACT_DIR, 'e2e_200pts_full.png');
    const scoreboardScreenshotPath = path.join(ARTIFACT_DIR, 'scoreboard_master.png');

    await page.screenshot({ path: fullScreenshotPath, fullPage: true });
    const scoreboardEl = await page.$('#scoreboard');
    if (scoreboardEl) {
      await scoreboardEl.screenshot({ path: scoreboardScreenshotPath });
    }
    console.log(`📸 풀페이지 스크린샷: ${fullScreenshotPath}`);
    console.log(`📸 전광판 스크린샷: ${scoreboardScreenshotPath}`);

  } catch (err) {
    console.error('❌ E2E 테스트 실행 중 오류 발생:', err);
    testResults.push({ title: '테스트 실행 오류', pass: false, extra: err.message });
  } finally {
    await browser.close();
  }

  const passed = testResults.filter(t => t.pass).length;
  const failed = testResults.filter(t => !t.pass).length;
  console.log('\n==============================================');
  console.log(`📊 E2E 테스트 결과 요약: 총 ${testResults.length}개 항목 중 ${passed} 통과, ${failed} 실패`);
  if (failed === 0) {
    console.log('🎉 200점 만점 퀘스트 E2E 검증 대성공!');
  }
  console.log('==============================================\n');
  process.exit(failed === 0 ? 0 : 1);
}

runE2ETest();
