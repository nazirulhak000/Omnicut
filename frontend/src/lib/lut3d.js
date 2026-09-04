// 3D LUT colour grading for the canvas preview, matching what
// video_editor.py's `lut3d` filter does to the rendered file. Before this the
// Filter picker changed nothing on screen: the grade only appeared after a
// render, so choosing one was guesswork.
//
// The grade is applied to the composited video layer only -- the same place
// the render applies it, before the sticker overlay and the subtitle burn, so
// a brand-coloured badge and the caption colours are never re-graded.

/**
 * Parses an Adobe .cube file into a flat RGB table.
 *
 * Returns { size, data } where `data` is Float32Array(size^3 * 3) in the
 * file's own order: red varies fastest, then green, then blue -- which is
 * also the memory order WebGL wants for a 3D texture.
 */
export function parseCube(text) {
  let size = 0;
  let domainMin = [0, 0, 0];
  let domainMax = [1, 1, 1];
  const values = [];

  for (const rawLine of String(text).split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const upper = line.toUpperCase();
    if (upper.startsWith('TITLE')) continue;
    if (upper.startsWith('LUT_3D_SIZE')) {
      size = parseInt(line.split(/\s+/)[1], 10);
      continue;
    }
    if (upper.startsWith('LUT_1D_SIZE')) {
      throw new Error('1D LUTs are not supported');
    }
    if (upper.startsWith('DOMAIN_MIN')) {
      domainMin = line.split(/\s+/).slice(1, 4).map(Number);
      continue;
    }
    if (upper.startsWith('DOMAIN_MAX')) {
      domainMax = line.split(/\s+/).slice(1, 4).map(Number);
      continue;
    }
    const parts = line.split(/\s+/);
    if (parts.length < 3) continue;
    const r = Number(parts[0]);
    const g = Number(parts[1]);
    const b = Number(parts[2]);
    if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) continue;
    values.push(r, g, b);
  }

  if (!size || values.length !== size * size * size * 3) {
    throw new Error(`bad .cube: LUT_3D_SIZE ${size} needs ${size ** 3 * 3} numbers, found ${values.length}`);
  }
  return { size, data: Float32Array.from(values), domainMin, domainMax };
}

/**
 * Trilinear sample of a parsed LUT, the same interpolation ffmpeg's lut3d
 * defaults to. Kept here so the grade can be checked against a real render
 * without a browser -- the WebGL path below leaves the identical
 * interpolation to the GPU's linear filtering.
 *
 * `rgb` and the result are 0..1.
 */
export function sampleLut(lut, r, g, b) {
  const { size, data } = lut;
  const last = size - 1;
  const coord = (v) => Math.min(last, Math.max(0, v * last));
  const cr = coord(r);
  const cg = coord(g);
  const cb = coord(b);
  const r0 = Math.floor(cr);
  const g0 = Math.floor(cg);
  const b0 = Math.floor(cb);
  const r1 = Math.min(last, r0 + 1);
  const g1 = Math.min(last, g0 + 1);
  const b1 = Math.min(last, b0 + 1);
  const fr = cr - r0;
  const fg = cg - g0;
  const fb = cb - b0;

  // Red varies fastest in a .cube file.
  const at = (ri, gi, bi) => (ri + gi * size + bi * size * size) * 3;
  const out = [0, 0, 0];
  for (let c = 0; c < 3; c++) {
    const c000 = data[at(r0, g0, b0) + c];
    const c100 = data[at(r1, g0, b0) + c];
    const c010 = data[at(r0, g1, b0) + c];
    const c110 = data[at(r1, g1, b0) + c];
    const c001 = data[at(r0, g0, b1) + c];
    const c101 = data[at(r1, g0, b1) + c];
    const c011 = data[at(r0, g1, b1) + c];
    const c111 = data[at(r1, g1, b1) + c];
    const x00 = c000 + (c100 - c000) * fr;
    const x10 = c010 + (c110 - c010) * fr;
    const x01 = c001 + (c101 - c001) * fr;
    const x11 = c011 + (c111 - c011) * fr;
    const y0 = x00 + (x10 - x00) * fg;
    const y1 = x01 + (x11 - x01) * fg;
    out[c] = y0 + (y1 - y0) * fb;
  }
  return out;
}

const VERT_SRC = `#version 300 es
in vec2 aPos;
out vec2 vUv;
void main() {
  vUv = aPos * 0.5 + 0.5;
  gl_Position = vec4(aPos, 0.0, 1.0);
}`;

// The half-texel inset is what makes GPU sampling agree with ffmpeg: a 3D
// texture's outer half-texel is the clamp region, so feeding 0..1 straight in
// would flatten the two ends of the grade.
const FRAG_SRC = `#version 300 es
precision highp float;
precision highp sampler3D;
uniform sampler2D uFrame;
uniform sampler3D uLut;
uniform float uStrength;
uniform float uLutSize;
in vec2 vUv;
out vec4 fragColor;
void main() {
  vec4 src = texture(uFrame, vec2(vUv.x, 1.0 - vUv.y));
  vec3 scale = vec3((uLutSize - 1.0) / uLutSize);
  vec3 offset = vec3(1.0 / (2.0 * uLutSize));
  vec3 graded = texture(uLut, clamp(src.rgb, 0.0, 1.0) * scale + offset).rgb;
  fragColor = vec4(mix(src.rgb, graded, uStrength), src.a);
}`;

function compile(gl, type, source) {
  const sh = gl.createShader(type);
  gl.shaderSource(sh, source);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(sh);
    gl.deleteShader(sh);
    throw new Error(`shader: ${log}`);
  }
  return sh;
}

/**
 * A WebGL2 pass that grades one canvas into another.
 *
 * Returns null when WebGL2 (or 3D textures) is unavailable, so the caller can
 * carry on ungraded rather than showing a black frame -- and say so, instead
 * of quietly lying about the grade.
 */
export function createLutRenderer(width, height) {
  const canvas = typeof document !== 'undefined' ? document.createElement('canvas') : null;
  if (!canvas) return null;
  canvas.width = width;
  canvas.height = height;
  const gl = canvas.getContext('webgl2', { premultipliedAlpha: false, antialias: false });
  if (!gl) return null;

  let program;
  try {
    program = gl.createProgram();
    gl.attachShader(program, compile(gl, gl.VERTEX_SHADER, VERT_SRC));
    gl.attachShader(program, compile(gl, gl.FRAGMENT_SHADER, FRAG_SRC));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(program));
    }
  } catch {
    return null;
  }

  const quad = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, quad);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const aPos = gl.getAttribLocation(program, 'aPos');
  gl.enableVertexAttribArray(aPos);
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

  const frameTex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, frameTex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

  const lutTex = gl.createTexture();
  let uploadedLut = null;

  const uFrame = gl.getUniformLocation(program, 'uFrame');
  const uLut = gl.getUniformLocation(program, 'uLut');
  const uStrength = gl.getUniformLocation(program, 'uStrength');
  const uLutSize = gl.getUniformLocation(program, 'uLutSize');

  function uploadLut(lut) {
    if (uploadedLut === lut) return;
    gl.bindTexture(gl.TEXTURE_3D, lutTex);
    gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_WRAP_R, gl.CLAMP_TO_EDGE);
    const n = lut.size ** 3;
    const rgba = new Uint8Array(n * 4);
    for (let i = 0; i < n; i++) {
      rgba[i * 4] = Math.round(Math.min(1, Math.max(0, lut.data[i * 3])) * 255);
      rgba[i * 4 + 1] = Math.round(Math.min(1, Math.max(0, lut.data[i * 3 + 1])) * 255);
      rgba[i * 4 + 2] = Math.round(Math.min(1, Math.max(0, lut.data[i * 3 + 2])) * 255);
      rgba[i * 4 + 3] = 255;
    }
    gl.texImage3D(gl.TEXTURE_3D, 0, gl.RGBA8, lut.size, lut.size, lut.size, 0,
                  gl.RGBA, gl.UNSIGNED_BYTE, rgba);
    uploadedLut = lut;
  }

  return {
    canvas,
    /** Grades `source` (a canvas) in place on this renderer's own canvas. */
    apply(source, lut, strength) {
      if (!lut || !(strength > 0.001)) return null;
      gl.useProgram(program);
      uploadLut(lut);

      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, frameTex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source);
      gl.uniform1i(uFrame, 0);

      gl.activeTexture(gl.TEXTURE1);
      gl.bindTexture(gl.TEXTURE_3D, lutTex);
      gl.uniform1i(uLut, 1);

      gl.uniform1f(uStrength, Math.min(1, Math.max(0, strength)));
      gl.uniform1f(uLutSize, lut.size);

      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.bindBuffer(gl.ARRAY_BUFFER, quad);
      gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      return canvas;
    },
    dispose() {
      gl.deleteTexture(frameTex);
      gl.deleteTexture(lutTex);
      gl.deleteBuffer(quad);
      gl.deleteProgram(program);
      uploadedLut = null;
    },
  };
}

const cubeCache = new Map();

/** Fetches and parses a .cube once per URL. */
export function loadCube(url) {
  if (!url) return Promise.resolve(null);
  const hit = cubeCache.get(url);
  if (hit) return hit;
  const pending = fetch(url)
    .then((r) => r.text())
    .then((text) => parseCube(text))
    .catch(() => {
      cubeCache.delete(url);
      return null;
    });
  cubeCache.set(url, pending);
  return pending;
}
