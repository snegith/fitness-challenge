/**
 * App — root component, routing, and token-check on load.
 *
 * Flow (SRS §10):
 *   Stored token exists → navigate to Dashboard
 *   No token            → navigate to Register / Login
 *
 * "Switch user" action (Dashboard) clears the stored token and
 * returns to Register/Login — no server-side session to invalidate
 * because the JWT is stateless (SRS §2.3).
 */

// TODO: implement routing with react-router-dom
// TODO: check localStorage for an existing token on load

export default function App() {
  return null; // placeholder
}
