/* Sfx — процедурный звук на WebAudio.
 * Никаких mp3: всё синтезируется на лету, поэтому игра весит копейки.
 */

class Sfx {
  constructor() {
    this.ctx = null;
    this.master = null;
    this.muted = false;
  }

  // AudioContext можно создать только после действия пользователя
  init() {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    if (!this.ctx) {
      this.ctx = new AC();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0.45;
      this.master.connect(this.ctx.destination);
    }
    if (this.ctx.state === 'suspended') this.ctx.resume();
  }

  get ready() {
    return !!this.ctx && !this.muted;
  }

  toggle() {
    this.muted = !this.muted;
    return this.muted;
  }

  env(gain, t, attack, release, peak) {
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(peak, t + attack);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + attack + release);
  }

  // "шлёп" при посадке + нота
  plop(freq) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;

    const o = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    o.type = 'sine';
    o.frequency.setValueAtTime(freq * 2.1, t);
    o.frequency.exponentialRampToValueAtTime(freq, t + 0.07);
    this.env(g, t, 0.008, 0.3, 0.5);
    o.connect(g);
    g.connect(this.master);
    o.start(t);
    o.stop(t + 0.36);

    this.noise(0.05, 1200, 0.22);
  }

  noise(dur, cut, vol) {
    if (!this.ready) return;
    const sr = this.ctx.sampleRate;
    const len = Math.max(1, Math.floor(sr * dur));
    const buf = this.ctx.createBuffer(1, len, sr);
    const data = buf.getChannelData(0);
    for (let i = 0; i < len; i++) {
      data[i] = (Math.random() * 2 - 1) * (1 - i / len);
    }

    const src = this.ctx.createBufferSource();
    src.buffer = buf;

    const f = this.ctx.createBiquadFilter();
    f.type = 'lowpass';
    f.frequency.value = cut;

    const g = this.ctx.createGain();
    g.gain.value = vol;

    src.connect(f);
    f.connect(g);
    g.connect(this.master);
    src.start();
  }

  drip() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    const o = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    o.type = 'sine';
    o.frequency.setValueAtTime(1500, t);
    o.frequency.exponentialRampToValueAtTime(700, t + 0.07);
    this.env(g, t, 0.004, 0.09, 0.1);
    o.connect(g);
    g.connect(this.master);
    o.start(t);
    o.stop(t + 0.12);
  }

  perfect() {
    if (!this.ready) return;
    const notes = [1046.5, 1568.0];
    notes.forEach((f, i) => {
      const t = this.ctx.currentTime + i * 0.06;
      const o = this.ctx.createOscillator();
      const g = this.ctx.createGain();
      o.type = 'triangle';
      o.frequency.value = f;
      this.env(g, t, 0.005, 0.13, 0.16);
      o.connect(g);
      g.connect(this.master);
      o.start(t);
      o.stop(t + 0.16);
    });
  }

  gameOver() {
    if (!this.ready) return;
    const notes = [523.25, 392.0, 261.63];
    notes.forEach((f, i) => {
      const t = this.ctx.currentTime + i * 0.14;
      const o = this.ctx.createOscillator();
      const g = this.ctx.createGain();
      o.type = 'sine';
      o.frequency.value = f;
      this.env(g, t, 0.01, 0.24, 0.22);
      o.connect(g);
      g.connect(this.master);
      o.start(t);
      o.stop(t + 0.28);
    });
  }

  // скрип башни, когда она теряет устойчивость
  creak() {
    if (!this.ready) return;
    this.noise(0.35, 380, 0.16);

    const t = this.ctx.currentTime;
    const o = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    o.type = 'sawtooth';
    o.frequency.setValueAtTime(92, t);
    o.frequency.linearRampToValueAtTime(68, t + 0.4);
    this.env(g, t, 0.03, 0.4, 0.1);
    o.connect(g);
    g.connect(this.master);
    o.start(t);
    o.stop(t + 0.46);
  }

  collapse() {    if (!this.ready) return;
    this.noise(0.6, 700, 0.5);
    const t = this.ctx.currentTime;
    const o = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    o.type = 'sawtooth';
    o.frequency.setValueAtTime(320, t);
    o.frequency.exponentialRampToValueAtTime(55, t + 0.8);
    this.env(g, t, 0.01, 0.8, 0.18);
    o.connect(g);
    g.connect(this.master);
    o.start(t);
    o.stop(t + 0.85);
  }
}

const SFX = new Sfx();
