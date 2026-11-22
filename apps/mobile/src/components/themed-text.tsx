import { useSyncExternalStore } from 'react';
import { Platform, StyleSheet, Text, type TextProps, type TextStyle } from 'react-native';

import { Fonts, ThemeColor } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { getTextScale, subscribeTextScale } from '@/lib/textScale';

export type ThemedTextProps = TextProps & {
  type?: 'default' | 'title' | 'small' | 'smallBold' | 'subtitle' | 'link' | 'linkPrimary' | 'code';
  themeColor?: ThemeColor;
};

export function ThemedText({ style, type = 'default', themeColor, ...rest }: ThemedTextProps) {
  const theme = useTheme();
  // Text-size preference (Phase 7 item 9): every text re-renders when the
  // traveller changes the setting on the settings screen.
  const scale = useSyncExternalStore(subscribeTextScale, getTextScale, getTextScale);
  const base = styles[type] as TextStyle;
  const sized: TextStyle =
    scale === 1
      ? base
      : {
          ...base,
          fontSize: (base.fontSize ?? 16) * scale,
          lineHeight: (base.lineHeight ?? (base.fontSize ?? 16) * 1.4) * scale,
        };

  return <Text style={[{ color: theme[themeColor ?? 'text'] }, sized, style]} {...rest} />;
}

const styles = StyleSheet.create({
  small: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: 500,
  },
  smallBold: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: 700,
  },
  default: {
    fontSize: 16,
    lineHeight: 24,
    fontWeight: 500,
  },
  title: {
    fontSize: 48,
    fontWeight: 600,
    lineHeight: 52,
  },
  subtitle: {
    fontSize: 32,
    lineHeight: 44,
    fontWeight: 600,
  },
  link: {
    lineHeight: 30,
    fontSize: 14,
  },
  linkPrimary: {
    lineHeight: 30,
    fontSize: 14,
    color: '#3c87f7',
  },
  code: {
    fontFamily: Fonts.mono,
    fontWeight: Platform.select({ android: 700 }) ?? 500,
    fontSize: 12,
  },
});
