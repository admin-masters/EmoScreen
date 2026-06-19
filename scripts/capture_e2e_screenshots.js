const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const root = process.cwd();
const dataPath = path.join(root, "docs/e2e_testing/guide_data.json");
const outDir = path.join(root, "docs/e2e_testing/screenshots");
const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));

fs.mkdirSync(outDir, { recursive: true });

function shotPath(name) {
  return path.join(outDir, `${name}.png`);
}

async function screenshot(page, name) {
  await page.waitForTimeout(500);
  await page.screenshot({ path: shotPath(name), fullPage: false });
  console.log(`saved ${name}.png`);
}

async function launchBrowser() {
  try {
    return await chromium.launch({ channel: "chrome", headless: true });
  } catch (error) {
    return await chromium.launch({ headless: true });
  }
}

async function login(page) {
  const next = `/admin/bulk-upload/`;
  await page.goto(`${data.admin_login_url}?next=${encodeURIComponent(next)}`, { waitUntil: "networkidle" });
  await page.fill("#id_username", data.doctor_username);
  await page.fill("#id_password", data.doctor_password);
  await screenshot(page, "01-admin-sign-in");
  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle" }),
    page.click('input[type="submit"]'),
  ]);
}

async function fillPaidQuestions(page) {
  await page.evaluate(() => {
    document.querySelectorAll("#questions-block .q").forEach((block) => {
      const radio = block.querySelector('input[type="radio"]');
      if (radio) {
        radio.checked = true;
        radio.dispatchEvent(new Event("change", { bubbles: true }));
        return;
      }
      const dateInput = block.querySelector('input[type="date"]');
      if (dateInput) {
        dateInput.value = "2026-06-19";
        dateInput.dispatchEvent(new Event("input", { bubbles: true }));
        return;
      }
      const textInput = block.querySelector('input[type="text"]');
      if (textInput) {
        textInput.value = "No concerns noted in this field";
        textInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
  });
}

async function fillFreeQuestions(page) {
  await page.evaluate(() => {
    document.querySelectorAll(".q").forEach((block) => {
      const radio = block.querySelector('input[type="radio"]');
      if (radio) {
        radio.checked = true;
        radio.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
  });
}

(async () => {
  const browser = await launchBrowser();
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1050 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  await login(page);

  await page.goto(data.home_url, { waitUntil: "networkidle" });
  await screenshot(page, "02-public-entry");

  await page.goto(data.admin_bulk_upload_url, { waitUntil: "networkidle" });
  await screenshot(page, "03-admin-bulk-doctor-recruitment");

  await page.goto(data.legacy_clinic_url, { waitUntil: "networkidle" });
  await screenshot(page, "04-doctor-clinic-console");

  await page.fill("#id_parent_whatsapp", "9811223344");
  await page.selectOption("#id_share_form", "P:ES_0_2");
  await page.fill("#id_patient_name", "Aarav Guide Test");
  await page.selectOption("#id_price_variant", "INR_1");
  await screenshot(page, "05-doctor-share-paid-form");

  await page.selectOption("#id_share_form", "B:behavioral");
  await page.selectOption("#id_language", "en");
  await screenshot(page, "06-doctor-share-free-form");

  await page.goto(data.paid_entry_url, { waitUntil: "networkidle" });
  await screenshot(page, "07-parent-paid-order-entry");

  await page.goto(data.paid_payment_url, { waitUntil: "networkidle" });
  await screenshot(page, "08-payment-screen");

  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle" }),
    page.click("text=Complete Dummy Payment"),
  ]);
  await page.fill("#id_child_name", "Aarav Guide Test");
  await page.fill("#id_child_dob", "2022-01-01");
  await page.fill("#id_assessment_date", "2026-06-19");
  await page.selectOption("#id_gender", "male");
  await page.fill("#id_completed_by", "Mother");
  await page.check("#id_consent_given");
  await page.waitForTimeout(300);
  await screenshot(page, "09-paid-assessment-form");

  await fillPaidQuestions(page);
  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle" }),
    page.click("text=Review"),
  ]);
  await screenshot(page, "10-paid-review-answers");

  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle" }),
    page.click("text=Submit Final"),
  ]);
  await screenshot(page, "11-paid-report-screen");

  await page.goto(data.free_verify_url, { waitUntil: "networkidle" });
  await screenshot(page, "12-free-phone-verification");

  await page.fill('input[name="parent_phone"]', "9822334455");
  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle" }),
    page.click('button[type="submit"]'),
  ]);
  await screenshot(page, "13-language-selection");

  await page.goto(data.free_screen_url, { waitUntil: "networkidle" });
  await page.fill('input[name="patient_name"]', "Meera Free Guide");
  await page.fill('input[name="parent_phone"]', "9822334455");
  await page.fill('input[name="patient_email"]', "parent.free@example.com");
  await page.fill('input[name="dob"]', "2020-01-01");
  await page.selectOption('select[name="gender"]', "Female");
  await screenshot(page, "14-free-screening-form");

  await fillFreeQuestions(page);
  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle" }),
    page.click('button[type="submit"]'),
  ]);
  await screenshot(page, "15-free-result-screen");

  await page.goto(data.self_start_url, { waitUntil: "networkidle" });
  await screenshot(page, "16-self-screen-start");

  await page.goto(data.workflow_dashboard_url, { waitUntil: "networkidle" });
  await screenshot(page, "17-workflow-audit-dashboard");

  await page.goto(data.paid_case_detail_url, { waitUntil: "networkidle" });
  await screenshot(page, "18-workflow-audit-detail");

  await browser.close();
})();
