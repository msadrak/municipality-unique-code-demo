const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const BASE_URL = 'http://127.0.0.1:8000';
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');

fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

const expectedTotals = {
  count: 2,
  personnel: 5,
  workedHours: 556.25,
  amount: 37300000,
};

function faToEn(value) {
  return String(value)
    .replace(/[۰-۹]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
    .replace(/٬/g, '')
    .replace(/٫/g, '.')
    .replace(/ريال|ریال/g, '')
    .trim();
}

function nearlyEqual(a, b, epsilon = 0.001) {
  return Math.abs(a - b) <= epsilon;
}

async function waitForAppReady(page) {
  await page.locator('aside').waitFor({ timeout: 30000 });
}

async function login(page, username, password) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('#username').fill(username);
  await page.locator('#password').fill(password);
  await page.getByRole('button', { name: /ورود به سامانه/ }).click();
  await waitForAppReady(page);
}

async function logout(page) {
  await page.evaluate(async () => {
    await fetch('/auth/logout', {
      method: 'POST',
      credentials: 'include',
    });
  });
  await page.context().clearCookies();
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
}

async function uploadSheet(page, title, region, filePath) {
  await page.getByRole('button', { name: /بارگذاری فایل/ }).click();
  await page.locator('#attendance-title').waitFor({ timeout: 30000 });
  await page.locator('#attendance-title').fill(title);
  await page.locator('#attendance-region').fill(region);
  await page.locator('#attendance-file').setInputFiles(filePath);
  await page.getByRole('button', { name: /ثبت و پردازش فایل/ }).click();
  await page.waitForFunction(() => {
    const titleInput = document.querySelector('#attendance-title');
    return titleInput && titleInput.value === '';
  }, null, { timeout: 30000 });
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1200 },
    locale: 'fa-IR',
  });
  const page = await context.newPage();

  const report = {
    uploads: [],
    inboxRowCount: 0,
    aggregationApi: null,
    aggregationUi: {},
    detail: {
      approveEnabled: false,
      rejectEnabled: false,
      statuses: [],
    },
    issues: [],
  };

  try {
    await login(page, 'operator_attendance', 'Attendance@123');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01-operator-home.png'), fullPage: true });

    const uploads = [
      {
        title: 'کارکرد فروردین منطقه ۱',
        region: 'منطقه ۱',
        filePath: path.resolve(__dirname, '..', '..', 'data', 'attendance_e2e', 'region1.xlsx'),
      },
      {
        title: 'کارکرد فروردین منطقه ۲',
        region: 'منطقه ۲',
        filePath: path.resolve(__dirname, '..', '..', 'data', 'attendance_e2e', 'region2.xlsx'),
      },
    ];

    for (const item of uploads) {
      await uploadSheet(page, item.title, item.region, item.filePath);
      report.uploads.push(item.title);
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02-upload-complete.png'), fullPage: true });

    await page.getByRole('button', { name: /کارتابل شیت‌ها/ }).click();
    await page.waitForURL(/\/attendance\/inbox$/);
    await page.waitForFunction(() => document.querySelectorAll('tbody tr').length >= 2, null, {
      timeout: 30000,
    });
    const inboxRows = page.locator('tbody tr');
    await inboxRows.first().waitFor({ timeout: 30000 });
    report.inboxRowCount = await inboxRows.count();
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03-attendance-inbox.png'), fullPage: true });

    await logout(page);

    await login(page, 'bahaderi', 'Attendance@123');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04-security-home.png'), fullPage: true });

    await page.getByRole('button', { name: /داشبورد تجمیعی حراست/ }).click();
    await page.waitForURL(/\/security\/aggregation$/);
    await page.locator('table').waitFor({ timeout: 30000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05-aggregation-dashboard.png'), fullPage: true });

    const aggregationApi = await page.evaluate(async () => {
      const response = await fetch('/api/attendance/reports/aggregation', {
        credentials: 'include',
      });
      const payload = await response.json();
      return {
        status: response.status,
        payload,
      };
    });
    report.aggregationApi = aggregationApi;

    const bodyText = await page.locator('body').innerText();
    report.aggregationUi.summaryText = bodyText;

    const items = aggregationApi.payload.items || [];
    const totals = items.reduce(
      (acc, item) => ({
        personnel: acc.personnel + item.total_personnel,
        workedHours: acc.workedHours + item.total_worked_hours,
        amount: acc.amount + item.total_amount,
      }),
      { personnel: 0, workedHours: 0, amount: 0 },
    );
    report.aggregationUi.computedTotals = totals;

    if (aggregationApi.status !== 200) {
      report.issues.push(`Aggregation endpoint returned HTTP ${aggregationApi.status}`);
    }
    if (aggregationApi.payload.count !== expectedTotals.count) {
      report.issues.push(`Expected ${expectedTotals.count} aggregated sheets, got ${aggregationApi.payload.count}`);
    }
    if (totals.personnel !== expectedTotals.personnel) {
      report.issues.push(`Expected personnel total ${expectedTotals.personnel}, got ${totals.personnel}`);
    }
    if (!nearlyEqual(totals.workedHours, expectedTotals.workedHours)) {
      report.issues.push(`Expected worked hours ${expectedTotals.workedHours}, got ${totals.workedHours}`);
    }
    if (totals.amount !== expectedTotals.amount) {
      report.issues.push(`Expected amount ${expectedTotals.amount}, got ${totals.amount}`);
    }

    const detailsButton = page.getByRole('button', { name: /جزئیات/ }).first();
    await detailsButton.click();
    try {
      await page.waitForFunction(() => /^\/attendance\/\d+$/.test(window.location.pathname), null, {
        timeout: 10000,
      });
    } catch (error) {
      report.issues.push('Clicking "جزئیات" on the aggregation dashboard did not navigate to the detail page.');
      await page.getByRole('button', { name: /کارتابل شیت‌ها/ }).click();
      await page.waitForFunction(() => window.location.pathname === '/attendance/inbox', null, {
        timeout: 30000,
      });
      await page.locator('tbody tr').first().click();
      await page.waitForFunction(() => /^\/attendance\/\d+$/.test(window.location.pathname), null, {
        timeout: 30000,
      });
    }
    await page.locator('[data-slot="badge"]').first().waitFor({ timeout: 30000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06-detail-before-transition.png'), fullPage: true });

    const approveButton = page.locator('button').filter({ hasText: /ت.?یید/ }).first();
    const rejectButton = page.locator('button').filter({ hasText: /^رد$/ }).first();
    report.detail.approveEnabled = await approveButton.isEnabled();
    report.detail.rejectEnabled = await rejectButton.isEnabled();
    const detailPath = await page.evaluate(() => window.location.pathname);
    const sheetId = Number(detailPath.split('/').pop());
    const readSheetStatus = async () => page.evaluate(async (targetSheetId) => {
      const response = await fetch(`/api/attendance/${targetSheetId}`, {
        credentials: 'include',
      });
      const payload = await response.json();
      return payload.status;
    }, sheetId);

    report.detail.statuses.push(await readSheetStatus());
    for (let i = 0; i < 3; i += 1) {
      await approveButton.click();
      await page.waitForTimeout(1200);
      report.detail.statuses.push(await readSheetStatus());
    }
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07-detail-after-transition.png'), fullPage: true });

    const expectedStatuses = [
      'DRAFT',
      'CREATOR_APPROVED',
      'COMPANY_REP_APPROVED',
      'SECURITY_APPROVED',
    ];
    if (JSON.stringify(report.detail.statuses) !== JSON.stringify(expectedStatuses)) {
      report.issues.push(
        `Unexpected workflow status sequence: ${JSON.stringify(report.detail.statuses)}`
      );
    }
  } finally {
    await browser.close();
  }

  process.stdout.write(JSON.stringify(report, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
