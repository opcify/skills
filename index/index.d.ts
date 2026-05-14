export interface ManagedBlock {
  tier: "general" | "template-scoped";
  templateScopes: string[];
  alwaysOn: boolean;
}
export interface SkillIndexEntry {
  slug: string;
  path: string;
  label: string;
  description: string;
  version: string;
  origin: "opcify" | "example";
  emoji?: string;
  managed?: ManagedBlock;
}
export interface SkillsIndex {
  version: string;
  repo: string;
  skills: SkillIndexEntry[];
}
declare const index: SkillsIndex;
export default index;
