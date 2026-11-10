// Microphone -> 16 kHz mono WAV, with simple voice-activity auto-stop.
// Prisma REST accepts WAV/MP3/OGG/FLAC/AAC/M4A (not WebM), so we encode WAV ourselves.

const WORKLET = `
class Tap extends AudioWorkletProcessor {
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (ch) this.port.postMessage(ch.slice(0));
    return true;
  }
}
registerProcessor('tap', Tap);`;

export class Recorder {
  constructor({ onLevel, onAutoStop, onNoisy, maxSeconds = 28, silenceMs = 1300 } = {}) {
    this.onLevel = onLevel || (() => {});
    this.onNoisy = onNoisy || (() => {});
    this.onAutoStop = onAutoStop || (() => {});
    this.maxSeconds = maxSeconds;
    this.silenceMs = silenceMs;
    this.recording = false;
  }

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
    });
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    const url = URL.createObjectURL(new Blob([WORKLET], { type: 'application/javascript' }));
    await this.ctx.audioWorklet.addModule(url);
    this.src = this.ctx.createMediaStreamSource(this.stream);
    this.node = new AudioWorkletNode(this.ctx, 'tap');
    this.chunks = [];
    this.recording = true;
    this.t0 = performance.now();
    this.heardSpeech = false;
    this.wasNoisy = false;
    this.lastLoud = performance.now();
    let noise = 0.01;
    this.node.port.onmessage = (e) => {
      if (!this.recording) return;
      const buf = e.data;
      this.chunks.push(buf);
      let sum = 0;
      for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
      const rms = Math.sqrt(sum / buf.length);
      // Room-noise estimate: falls fast, rises slowly. (It used to follow any sound quickly, so a
      // voice that started the instant the mic was tapped got learned as "background" and the
      // recording ended with "didn't hear anything".)
      if (!this.heardSpeech) noise = rms < noise ? 0.8 * noise + 0.2 * rms : 0.995 * noise + 0.005 * rms;
      const loud = rms > Math.max(0.02, noise * 3) || rms > 0.08;   // clearly loud always counts as speech
      const now = performance.now();
      // Heuristic: background above about -32 dBFS before speech starts -> warn the user.
      const noisyNow = !this.heardSpeech && now - this.t0 > 400 && noise > 0.025;
      if (noisyNow !== this.wasNoisy) { this.wasNoisy = noisyNow; this.onNoisy(noisyNow); }
      if (loud) { this.lastLoud = now; if (now - this.t0 > 150) this.heardSpeech = true; }
      this.onLevel(Math.min(1, rms * 8));
      const elapsed = (now - this.t0) / 1000;
      if ((this.heardSpeech && now - this.lastLoud > this.silenceMs) || elapsed > this.maxSeconds) {
        this.onAutoStop();
      }
    };
    this.src.connect(this.node);
  }

  async stop() {
    if (!this.recording) return null;
    this.recording = false;
    const rate = this.ctx.sampleRate;
    try { this.src.disconnect(); this.node.disconnect(); } catch (_) {}
    this.stream.getTracks().forEach((t) => t.stop());
    await this.ctx.close();
    const len = this.chunks.reduce((a, c) => a + c.length, 0);
    const all = new Float32Array(len);
    let o = 0;
    for (const c of this.chunks) { all.set(c, o); o += c.length; }
    const pcm = downsample(all, rate, 16000);
    return { blob: encodeWav(pcm, 16000), seconds: pcm.length / 16000, heardSpeech: this.heardSpeech };
  }
}

function downsample(input, from, to) {
  if (from === to) return input;
  const ratio = from / to;
  const out = new Float32Array(Math.floor(input.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const start = Math.floor(i * ratio), end = Math.min(input.length, Math.floor((i + 1) * ratio));
    let s = 0;
    for (let j = start; j < end; j++) s += input[j];
    out[i] = s / Math.max(1, end - start);   // box filter = cheap anti-aliasing
  }
  return out;
}

function encodeWav(samples, rate) {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, 'RIFF'); v.setUint32(4, 36 + samples.length * 2, true); w(8, 'WAVE');
  w(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  w(36, 'data'); v.setUint32(40, samples.length * 2, true);
  let o = 44;
  for (let i = 0; i < samples.length; i++, o += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buf], { type: 'audio/wav' });
}
