/**
 * Attendance calculation formulas and status classifications.
 * 
 * Rules:
 * - Minimum required attendance threshold is 75%.
 * - Status categories:
 *     >= 75%: Safe / Requirement satisfied
 *     65% <= percentage < 75%: Conditionally eligible
 *     < 65%: Critical
 * 
 * Mathematical Formulas:
 * - Classes can miss while maintaining R% (75%):
 *     Find max x such that: A / (T + x) >= R / 100
 *     => x = floor((100 * A - R * T) / R)
 *     (Returns 0 if already below R or exactly at R)
 * 
 * - Classes required to reach R% (75%):
 *     Find min x such that: (A + x) / (T + x) >= R / 100
 *     => x = ceil((R * T - 100 * A) / (100 - R))
 *     (Returns 0 if already at or above R)
 */

export const MIN_REQUIRED_ATTENDANCE = 75;

export type AttendanceStatusCategory = 'safe' | 'conditionally-eligible' | 'critical';

export function getStatusCategory(percentage: number): AttendanceStatusCategory {
  if (percentage >= MIN_REQUIRED_ATTENDANCE) {
    return 'safe';
  }
  if (percentage >= 65) {
    return 'conditionally-eligible';
  }
  return 'critical';
}

export function getStatusLabel(percentage: number): string {
  if (percentage >= MIN_REQUIRED_ATTENDANCE) {
    return 'Safe';
  }
  if (percentage >= 65) {
    return 'Conditionally eligible';
  }
  return 'Critical';
}

export function calculateCanMiss(attended: number, total: number, required: number = MIN_REQUIRED_ATTENDANCE): number {
  if (total <= 0 || attended <= 0) return 0;
  if ((attended / total) * 100 < required) return 0;
  const x = Math.floor((100 * attended - required * total) / required);
  return Math.max(0, x);
}

export function calculateClassesRequired(attended: number, total: number, required: number = MIN_REQUIRED_ATTENDANCE): number {
  if (total <= 0) return 0;
  if ((attended / total) * 100 >= required) return 0;
  const remaining = 100 - required;
  if (remaining <= 0) return 0;
  const x = Math.ceil((required * total - 100 * attended) / remaining);
  return Math.max(0, x);
}
