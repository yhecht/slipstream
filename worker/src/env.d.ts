// Worker config - all set as secrets by the installer (`wrangler secret put`),
// so nothing sensitive lives in the repo. Merges into the generated Env type.
interface Env {
  /** "owner/repo" of your private data repo holding data/activities.csv */
  DATA_REPO: string;
  /** Fine-grained GitHub token, read-only Contents scope on DATA_REPO */
  GITHUB_TOKEN: string;
  /** Unguessable path segment gating access to the connector */
  MCP_SECRET: string;
}
