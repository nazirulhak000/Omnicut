/**
 * Maps Backend Error Payloads into User-Friendly Thai Messages and Suggestions.
 */

export const DEFAULT_ERROR_SUGGESTIONS = {
  user_correctable: 'กรุณาตรวจสอบไฟล์มีเดียหรือข้อมูลที่ป้อนเข้า แล้วลองใหม่อีกครั้ง',
  ffmpeg: 'กรุณาตรวจสอบว่าไฟล์วิดีโอไม่เสียหายและเป็นฟอร์แมตมาตรฐาน (MP4/MOV)',
  ai_provider: 'ระบบจะสลับใช้โมเดลสำรอง หรือกรุณารอสักครู่แล้วลองใหม่',
  system_io: 'กรุณาตรวจสอบพื้นที่ว่างบนดิสก์และสิทธิ์การเข้าถึงไฟล์',
  internal: 'กรุณากดลองใหม่อีกครั้ง หรือตรวจสอบประวัติการทำงานใน Activity Center',
};

/**
 * Formats an error response or exception payload into structured display information.
 *
 * @param {Object|string} err - Raw error string or backend error object
 * @returns {Object} { message, suggestion, category, code }
 */
export function formatAppError(err) {
  if (!err) {
    return {
      message: 'เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุ',
      suggestion: 'กรุณากดลองใหม่อีกครั้ง',
      category: 'internal',
      code: 'UNKNOWN_ERROR',
    };
  }

  if (typeof err === 'string') {
    return {
      message: err,
      suggestion: 'กรุณากดลองใหม่อีกครั้ง',
      category: 'internal',
      code: 'GENERAL_ERROR',
    };
  }

  const category = err.error_category || err.category || 'internal';
  const message = err.error || err.message_th || err.message || 'เกิดข้อผิดพลาดในการประมวลผล';
  const suggestion =
    err.suggestion_th ||
    err.suggestion ||
    DEFAULT_ERROR_SUGGESTIONS[category] ||
    DEFAULT_ERROR_SUGGESTIONS.internal;
  const code = err.error_code || err.code || 'APP_ERROR';

  return {
    message,
    suggestion,
    category,
    code,
  };
}
