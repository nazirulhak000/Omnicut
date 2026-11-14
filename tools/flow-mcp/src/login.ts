#!/usr/bin/env node
// One-time setup: opens the dedicated Chrome profile on Flow so the user can sign in by hand.
import { getFlowPage, PROFILE_DIR } from "./chrome.js";

const page = await getFlowPage();
await page.bringToFront();
console.log("==================================================================");
console.log(`Chrome is open on: ${page.url()}`);
console.log(`Profile: ${PROFILE_DIR}`);
console.log("------------------------------------------------------------------");
console.log(">> กรุณาล็อกอินบัญชี Google ในหน้าต่าง Chrome ที่เปิดขึ้นมา");
console.log(">> เมื่อล็อกอินเสร็จและเปิดหน้าโปรเจกต์ Google Flow เรียบร้อยแล้ว");
console.log(">> กดปุ่ม [Enter] ในหน้าต่างนี้เพื่อบันทึก Session และเสร็จสิ้น...");
console.log("==================================================================");

// Wait for user to press Enter so Chrome stays open
await new Promise<void>((resolve) => {
  process.stdin.resume();
  process.stdin.once("data", () => resolve());
});

console.log("บันทึก Session สำเร็จเรียบร้อย!");
process.exit(0);
