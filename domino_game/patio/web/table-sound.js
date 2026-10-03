export class TableSound {
  constructor() {
    this.enabled = false;
    try {
      this.enabled = localStorage.getItem("patio-sound") === "on";
    } catch {
      /* Private browsers may deny preference storage. */
    }
  }

  async toggle() {
    const enabled = !this.enabled;
    if (enabled) {
      this.context ??= new AudioContext();
      await this.context.resume();
    }
    this.enabled = enabled;
    try {
      localStorage.setItem("patio-sound", this.enabled ? "on" : "off");
    } catch {
      /* Sound still works without persistence. */
    }
    if (this.enabled) this.play("tile");
    return this.enabled;
  }

  async unlock() {
    if (!this.enabled) return;
    this.context ??= new AudioContext();
    await this.context.resume();
  }

  play(kind) {
    const context = this.context;
    if (!this.enabled || context?.state !== "running") return;
    const now = context.currentTime;
    if (kind === "turn") {
      const oscillator = context.createOscillator(),
        gain = context.createGain();
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(660, now);
      oscillator.frequency.exponentialRampToValueAtTime(440, now + 0.1);
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.045, now + 0.008);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.14);
      oscillator.connect(gain).connect(context.destination);
      oscillator.start(now);
      oscillator.stop(now + 0.15);
      oscillator.onended = () => {
        oscillator.disconnect();
        gain.disconnect();
      };
      return;
    }
    // A filtered impact and a short wooden resonance, generated locally.
    const duration = 0.11,
      buffer = context.createBuffer(1, Math.ceil(context.sampleRate * duration), context.sampleRate);
    const samples = buffer.getChannelData(0);
    for (let i = 0; i < samples.length; i++)
      samples[i] = (Math.random() * 2 - 1) * Math.exp((-i / context.sampleRate) * 65);
    const impact = context.createBufferSource(),
      filter = context.createBiquadFilter(),
      gain = context.createGain();
    impact.buffer = buffer;
    filter.type = "lowpass";
    filter.frequency.value = 2200;
    gain.gain.value = 0.22;
    impact.connect(filter).connect(gain).connect(context.destination);
    impact.start(now);
    impact.onended = () => {
      impact.disconnect();
      filter.disconnect();
      gain.disconnect();
    };
    const resonance = context.createOscillator(),
      body = context.createGain();
    resonance.frequency.setValueAtTime(175, now);
    resonance.frequency.exponentialRampToValueAtTime(95, now + 0.1);
    body.gain.setValueAtTime(0.1, now);
    body.gain.exponentialRampToValueAtTime(0.0001, now + 0.12);
    resonance.connect(body).connect(context.destination);
    resonance.start(now);
    resonance.stop(now + 0.13);
    resonance.onended = () => {
      resonance.disconnect();
      body.disconnect();
    };
  }
}
