/**
 * Voice guidance / read-aloud (Phase 6 item 7, P1 — grounded English only).
 *
 * Reads the deterministic step instructions produced by the backend templates
 * using the device TTS engine (`expo-speech`). Grounding rules carried over:
 * - the spoken text is **exactly** the step's template wording (never
 *   paraphrased, never AI-generated), so what is heard matches what is shown;
 * - **English only** until native review (D-7) — si/ta steps are read in
 *   English with the same fallback the visual templates use;
 * - the preference (`voice_guidance`) must be on for the control to appear;
 *   nothing is read automatically — reading always starts from an explicit
 *   tap (manual-first, like progress itself).
 *
 * Interruption controls (plan item 7 requirement): speech stops when the
 * screen unmounts, when the traveller pauses/ends the journey, when the
 * control is toggled off, or when a new read starts (replaces, never
 * overlaps). Language, rate and pitch follow sensible defaults; the device's
 * system accessibility settings still govern volume/mixing.
 */

import * as Speech from 'expo-speech';

export interface ReadAloudController {
  /** True while text is being spoken. */
  readonly isSpeaking: boolean;
  /** Speak one or more step texts (in order, sequentially). */
  speak: (texts: string[]) => void;
  /** Stop any current speech. */
  stop: () => void;
  /** Subscribe to speaking-state changes; returns the unsubscribe fn. */
  onSpeakingChange: (listener: (speaking: boolean) => void) => () => void;
}

/** Builds a controller bound to the injected Speech module (testable). */
export function createReadAloudController(
  speech: Pick<typeof Speech, 'speak' | 'stop'>,
  options: { language?: string; rate?: number } = {},
): ReadAloudController {
  let speaking = false;
  const listeners = new Set<(speaking: boolean) => void>();

  function setSpeaking(value: boolean) {
    speaking = value;
    for (const listener of listeners) {
      listener(value);
    }
  }

  return {
    get isSpeaking() {
      return speaking;
    },
    speak(texts: string[]) {
      // Replace, never overlap: stop anything current first.
      speech.stop();
      setSpeaking(true);
      const queue = texts.filter((text) => text.trim().length > 0);
      queue.forEach((text, index) => {
        const isLast = index === queue.length - 1;
        speech.speak(text, {
          language: options.language ?? 'en-US',
          rate: options.rate ?? 0.95,
          onDone: () => {
            if (isLast) {
              setSpeaking(false);
            }
          },
          onStopped: () => {
            if (isLast) {
              setSpeaking(false);
            }
          },
          onError: () => {
            setSpeaking(false);
          },
        });
      });
    },
    stop() {
      speech.stop();
      setSpeaking(false);
    },
    onSpeakingChange(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}

/** The app-wide controller over the real device TTS engine. */
export const readAloud = createReadAloudController(Speech);

/**
 * Formats the spoken sequence for one journey step: the deterministic step
 * text followed by the next step's text when present (the "Do this now"
 * card shows current + next — voice mirrors that exactly).
 */
export function stepSpeechTexts(
  current: { text: string } | null,
  next: { text: string } | null,
): string[] {
  const texts: string[] = [];
  if (current) {
    texts.push(current.text);
  }
  if (next) {
    texts.push(next.text);
  }
  return texts;
}
