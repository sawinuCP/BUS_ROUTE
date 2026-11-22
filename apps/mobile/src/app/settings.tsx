import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Switch, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import {
  DEFAULT_PREFERENCES,
  readPreferences,
  savePreferences,
  type PlanPriority,
  type PrefLanguage,
  type UserPreferences,
} from '@/lib/preferencesDb';
import { setTextScale, TEXT_SCALE_OPTIONS } from '@/lib/textScale';

/**
 * User preferences (Phase 7, plan item 9) — local-first: everything is stored
 * on the device only (SQLite) and applied to the next journey plan. There is
 * no account and nothing is synced (plan item 10 defers account sync).
 *
 * Honesty: si/ta instruction text falls back to English until native review
 * (D-7); rail rides require a verified station order (a preference can never
 * bypass a grounding rule); read-aloud arrives with the grounded AI phase
 * (P1) — the preference is stored now.
 */

const LANGUAGES: { value: PrefLanguage; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'si', label: 'සිංහල (fallback: English)' },
  { value: 'ta', label: 'தமிழ் (fallback: English)' },
];

const PRIORITIES: { value: PlanPriority; label: string }[] = [
  { value: 'fastest', label: 'Fastest' },
  { value: 'least_walking', label: 'Least walking' },
  { value: 'fewest_transfers', label: 'Fewest transfers' },
  { value: 'simplest', label: 'Simplest' },
];

const WALKING_CAPS = [500, 1000, 1500, 2000, 3000, 5000];
const TRANSFERS = [0, 1, 2, 3];

function OptionRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.row}>
      <ThemedText type="smallBold">{label}</ThemedText>
      <View style={styles.options}>{children}</View>
    </View>
  );
}

function OptionButton({
  label,
  selected,
  onPress,
  testID,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
  testID: string;
}) {
  return (
    <Pressable
      style={[styles.option, selected ? styles.optionSelected : null]}
      onPress={onPress}
      testID={testID}
    >
      <ThemedText type="smallBold">{selected ? '✓ ' : ''}{label}</ThemedText>
    </Pressable>
  );
}

export default function SettingsScreen() {
  const [prefs, setPrefs] = useState<UserPreferences>(() => readPreferences());

  function update(patch: Partial<UserPreferences>) {
    const next = savePreferences(patch);
    setPrefs(next);
    if (patch.text_scale !== undefined) {
      setTextScale(patch.text_scale);
    }
  }

  return (
    <ThemedView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <ThemedText type="subtitle">Settings</ThemedText>
        <ThemedText type="small" themeColor="textSecondary" testID="local-first-note">
          Saved on this device only — no account, nothing synced or uploaded. Planning
          preferences apply from your next plan.
        </ThemedText>

        <OptionRow label="Instruction language">
          {LANGUAGES.map((language) => (
            <OptionButton
              key={language.value}
              label={language.label}
              selected={prefs.language === language.value}
              onPress={() => update({ language: language.value })}
              testID={`pref-language-${language.value}`}
            />
          ))}
          <ThemedText type="small" themeColor="textSecondary">
            si/ta instruction text is rendered in English until native review is complete (D-7).
          </ThemedText>
        </OptionRow>

        <OptionRow label="Journey priority">
          {PRIORITIES.map((priority) => (
            <OptionButton
              key={priority.value}
              label={priority.label}
              selected={prefs.priority === priority.value}
              onPress={() => update({ priority: priority.value })}
              testID={`pref-priority-${priority.value}`}
            />
          ))}
        </OptionRow>

        <OptionRow label="Maximum walking (one leg, routed distance)">
          {WALKING_CAPS.map((cap) => (
            <OptionButton
              key={cap}
              label={`${cap} m`}
              selected={prefs.max_walking_m === cap}
              onPress={() => update({ max_walking_m: cap })}
              testID={`pref-walk-${cap}`}
            />
          ))}
        </OptionRow>

        <OptionRow label="Maximum transfers">
          {TRANSFERS.map((count) => (
            <OptionButton
              key={count}
              label={count === 0 ? 'Direct only' : `${count}`}
              selected={prefs.max_transfers === count}
              onPress={() => update({ max_transfers: count })}
              testID={`pref-transfers-${count}`}
            />
          ))}
        </OptionRow>

        <View style={styles.row}>
          <ThemedText type="smallBold">Modes</ThemedText>
          <View style={styles.options}>
            <OptionButton label="Bus" selected onPress={() => undefined} testID="pref-mode-bus" />
            <View style={styles.switchRow}>
              <Switch
                value={prefs.allowed_modes.includes('rail')}
                onValueChange={(value) =>
                  update({
                    allowed_modes: value ? ['bus', 'rail'] : DEFAULT_PREFERENCES.allowed_modes,
                  })
                }
                testID="pref-mode-rail"
              />
              <ThemedText type="small">Allow rail</ThemedText>
            </View>
          </View>
          <ThemedText type="small" themeColor="textSecondary">
            Rail rides additionally require a verified station order — a preference can never
            bypass that rule.
          </ThemedText>
        </View>

        <OptionRow label="Text size">
          {TEXT_SCALE_OPTIONS.map((option) => (
            <OptionButton
              key={option.value}
              label={option.label}
              selected={prefs.text_scale === option.value}
              onPress={() => update({ text_scale: option.value })}
              testID={`pref-text-${option.label.toLowerCase()}`}
            />
          ))}
        </OptionRow>

        <View style={styles.row}>
          <View style={styles.switchRow}>
            <Switch
              value={prefs.voice_guidance}
              onValueChange={(value) => update({ voice_guidance: value })}
              testID="pref-voice"
            />
            <ThemedText type="smallBold">Voice guidance (read steps aloud)</ThemedText>
          </View>
          <ThemedText type="small" themeColor="textSecondary">
            The preference is saved now; read-aloud arrives with the grounded AI assistance phase
            (P1).
          </ThemedText>
        </View>

        <ThemedText type="small" testID="prefs-saved">
          Preferences saved on this device.
        </ThemedText>
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: Spacing.three,
    gap: Spacing.two,
  },
  row: {
    gap: Spacing.one,
  },
  options: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  option: {
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#999',
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  optionSelected: {
    backgroundColor: 'rgba(32,138,239,0.15)',
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.one,
  },
});