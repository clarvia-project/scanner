/**
 * Central API configuration.
 *
 * All frontend files should import API_BASE from here
 * instead of declaring it locally.
 */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
