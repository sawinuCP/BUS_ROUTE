/**
 * In-memory hand-off of the last plan between screens (Phase 5).
 *
 * Expo Router params must be plain strings; a full plan with steps is too
 * large for a URL. The store holds only the most recent response for the
 * current session — plans are regenerated (or refreshed) on demand, so losing
 * this on app restart is acceptable and never fabricates a plan. Plans are
 * also saved server-side via `save: true` when persistence matters (Phase 4).
 */

import type { JourneyPlanResponse, PlanOption } from '@/lib/api';

let currentPlan: JourneyPlanResponse | null = null;

export function setPlan(plan: JourneyPlanResponse): void {
  currentPlan = plan;
}

export function getPlan(): JourneyPlanResponse | null {
  return currentPlan;
}

export function getOptionById(optionId: string | undefined): PlanOption | null {
  if (!optionId || currentPlan === null) {
    return null;
  }
  return currentPlan.options.find((option) => option.id === optionId) ?? null;
}

/** Test helper: forget the in-session plan. */
export function clearPlan(): void {
  currentPlan = null;
}
