/**
 * Voice read-aloud controller unit tests (Phase 6 item 7, P1).
 *
 * The controller is pure over an injected Speech double: what is asserted is
 * the grounding contract (spoken text == the step's template wording, in
 * order, never overlapping) and the interruption controls (stop replaces,
 * explicit stop, speaking-state notifications).
 */

import { createReadAloudController, stepSpeechTexts } from '@/lib/readAloud';

function fakeSpeech() {
  const speakCalls: { text: string; options: unknown }[] = [];
  let stopCount = 0;
  return {
    module: {
      speak: jest.fn((text: string, options?: Record<string, unknown>) => {
        speakCalls.push({ text, options: options ?? {} });
      }),
      stop: jest.fn(async () => {
        stopCount += 1;
      }),
    },
    speakCalls,
    stopCount: () => stopCount,
  };
}

describe('readAloud controller (Phase 6 item 7, P1)', () => {
  it('speaks each step text in order after replacing any current speech', () => {
    const speech = fakeSpeech();
    const controller = createReadAloudController(speech.module);

    controller.speak(['Board route 138 at Stop A.', 'Ride 12 stops to Kollupitiya.']);

    // Replace-never-overlap: a stop precedes every new read.
    expect(speech.stopCount()).toBe(1);
    expect(speech.speakCalls.map((call) => call.text)).toEqual([
      'Board route 138 at Stop A.',
      'Ride 12 stops to Kollupitiya.',
    ]);
    // English-only until native review (D-7): the TTS language is English.
    expect((speech.speakCalls[0].options as Record<string, unknown>).language).toBe('en-US');
    expect(controller.isSpeaking).toBe(true);
  });

  it('filters empty texts and notifies listeners of the speaking state', () => {
    const speech = fakeSpeech();
    const controller = createReadAloudController(speech.module);
    const states: boolean[] = [];
    controller.onSpeakingChange((speaking) => states.push(speaking));

    controller.speak(['Walk 320 m to Homagama Junction.', '   ']);

    expect(speech.speakCalls.map((call) => call.text)).toEqual(['Walk 320 m to Homagama Junction.']);
    expect(states).toEqual([true]);

    controller.stop();

    expect(states).toEqual([true, false]);
    expect(speech.stopCount()).toBe(2);
    expect(controller.isSpeaking).toBe(false);
  });

  it('unsubscribes listeners and keeps other listeners working', () => {
    const speech = fakeSpeech();
    const controller = createReadAloudController(speech.module);
    const first: boolean[] = [];
    const second: boolean[] = [];
    const unsubscribe = controller.onSpeakingChange((value) => first.push(value));
    controller.onSpeakingChange((value) => second.push(value));

    unsubscribe();
    controller.speak(['Alight at Kollupitiya Junction.']);

    expect(first).toEqual([]);
    expect(second).toEqual([true]);
  });

  it('mirrors the do-this-now card: current step then next step', () => {
    const current = { text: 'Walk 240 m to the boarding point.' };
    const next = { text: 'Board route 101 at A.' };

    expect(stepSpeechTexts(current, next)).toEqual([current.text, next.text]);
    expect(stepSpeechTexts(current, null)).toEqual([current.text]);
    expect(stepSpeechTexts(null, null)).toEqual([]);
  });
});
