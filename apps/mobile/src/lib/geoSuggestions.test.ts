/**
 * Pure GPS-suggestion safeguards (Phase 6 work item 5).
 *
 * The rule under test: a weak signal, a single fix, or a location jump can
 * NEVER fire a suggestion — only sustained (dwell) proximity with good
 * accuracy does. Suggestions are advisory; the traveller still confirms.
 */

import { distanceMeters, evaluateProximity, type LocationSample } from '@/lib/geoSuggestions';

const TARGET = { lat: 6.9107, lon: 79.8483, radius_m: 40, label: 'Board route 101 at A.' };

const sample = (lat: number, lon: number, accuracy_m = 10): LocationSample => ({
  lat,
  lon,
  accuracy_m,
});

describe('evaluateProximity safeguards', () => {
  it('does not suggest from a single sample, even dead-centre', () => {
    const result = evaluateProximity([sample(TARGET.lat, TARGET.lon)], TARGET);
    expect(result.suggest).toBe(false);
    expect(result.reason).toBe('dwell');
  });

  it('suggests only after sustained dwell inside the radius', () => {
    const samples = [
      sample(TARGET.lat + 0.0001, TARGET.lon), // ~11 m away
      sample(TARGET.lat + 0.0001, TARGET.lon),
      sample(TARGET.lat + 0.0001, TARGET.lon),
    ];
    const result = evaluateProximity(samples, TARGET);
    expect(result.suggest).toBe(true);
    expect(result.reason).toBe('dwell');
  });

  it('rejects samples with poor accuracy and resets the dwell run', () => {
    const good = sample(TARGET.lat, TARGET.lon);
    const weak = sample(TARGET.lat, TARGET.lon, 80); // accuracy worse than 50 m
    const samples = [good, good, weak, good, good];

    const result = evaluateProximity(samples, TARGET);
    // Only two valid samples remain after the weak one — below the dwell need.
    expect(result.suggest).toBe(false);
    expect(result.reason).toBe('dwell');
  });

  it('rejects implausible jumps (a glitch cannot trigger anything)', () => {
    const near = sample(TARGET.lat + 0.0001, TARGET.lon);
    const farJump = sample(TARGET.lat + 0.01, TARGET.lon); // > 1 km jump
    const back = sample(TARGET.lat + 0.0001, TARGET.lon);
    const samples = [near, near, farJump, back, back, back];

    const result = evaluateProximity(samples, TARGET);
    // The jump resets the run: only 3 valid samples after it, so dwell is met
    // only if all three are inside — they are, but the run restarted, so the
    // verdict depends on the trailing window; assert the jump is honoured.
    expect(result.suggest).toBe(true); // 3 consecutive valid inside samples
    const glitched = [near, farJump, back]; // only one valid sample after jump
    expect(evaluateProximity(glitched, TARGET).suggest).toBe(false);
  });

  it('does not suggest when dwelling outside the radius', () => {
    const samples = [
      sample(TARGET.lat + 0.005, TARGET.lon), // ~550 m away
      sample(TARGET.lat + 0.005, TARGET.lon),
      sample(TARGET.lat + 0.005, TARGET.lon),
    ];
    const result = evaluateProximity(samples, TARGET);
    expect(result.suggest).toBe(false);
    expect(result.reason).toBe('outside');
  });

  it('distanceMeters matches the known kilometre scale', () => {
    const metres = distanceMeters(6.9, 79.85, 7.0, 79.85);
    expect(metres).toBeGreaterThan(10_000);
    expect(metres).toBeLessThan(12_000);
  });
});
