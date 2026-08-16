// Vitest setup — extends expect() with DOM matchers.
import "@testing-library/jest-dom";

// Mock ResizeObserver for Recharts in jsdom
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
