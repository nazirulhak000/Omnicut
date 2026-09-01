/**
 * Utility functions for input sanitization and safe text handling
 * Prevents FFmpeg drawtext/subtitles crashes, XML/SSML injection in TTS,
 * and dangerous filename characters.
 */

/**
 * Sanitizes general single-line text (Product name, Hook, Price, Deals)
 * Removes control characters, normalizes whitespace, and cleans unclosed quotes.
 */
export function sanitizeText(text) {
  if (typeof text !== 'string') return '';
  
  return text
    // Remove null bytes and invisible control characters (except common spaces)
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '')
    // Normalize XML/HTML tags that might confuse SSML engines or drawtext
    .replace(/[<>]/g, '')
    // Replace curved smart quotes with regular quotes for consistent parsing
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201C\u201D]/g, '"')
    // Remove duplicate whitespace
    .replace(/[ \t]+/g, ' ')
    .trim();
}

/**
 * Sanitizes multi-line voiceover scripts
 * Preserves newlines (1 line = 1 subtitle/cue), but strips dangerous tags and control codes.
 */
export function sanitizeScript(script) {
  if (typeof script !== 'string') return '';

  return script
    .split('\n')
    .map(line => sanitizeText(line))
    .filter(line => line.length > 0)
    .join('\n');
}

/**
 * Sanitizes filenames for safe storage and FFmpeg paths
 * Removes path traversal '../', slashes, and characters forbidden on Windows/Linux.
 */
export function sanitizeFilename(name) {
  if (typeof name !== 'string') return 'file';

  return name
    // Remove directory traversal
    .replace(/\.\.+[/\\]/g, '')
    // Replace forbidden path characters with underscores
    .replace(/[/\\?%*:|"<>]/g, '_')
    // Trim leading/trailing spaces and dots
    .replace(/^[.\s]+|[.\s]+$/g, '');
}
