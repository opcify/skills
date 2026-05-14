import { test } from "node:test";
import assert from "node:assert/strict";
import { buildIndex } from "./build.mjs";

test("indexes an Opcify-managed skill from _meta.json", () => {
  const idx = buildIndex("../skills");
  const yf = idx.skills.find((s) => s.slug === "yahoo-finance");
  assert.ok(yf, "yahoo-finance present");
  assert.equal(yf.origin, "opcify");
  assert.equal(yf.path, "skills/yahoo-finance");
  assert.equal(yf.label, "Yahoo Finance");
  assert.equal(yf.managed.tier, "template-scoped");
  assert.deepEqual(yf.managed.templateScopes, ["investing_trading_firm"]);
});

test("indexes an Anthropic example skill with origin=example", () => {
  const idx = buildIndex("../skills");
  const pdf = idx.skills.find((s) => s.slug === "pdf");
  assert.ok(pdf, "pdf present");
  assert.equal(pdf.origin, "example");
  assert.equal(pdf.managed, undefined);
});

test("plain (unquoted) description is captured cleanly", () => {
  const idx = buildIndex("../skills");
  const pdf = idx.skills.find((s) => s.slug === "pdf");
  assert.ok(pdf.description.length > 0, "pdf has a description");
  assert.ok(!pdf.description.startsWith('"'), "no stray leading quote");
});

test("double-quoted description with escaped quotes is unescaped, no stray delimiters", () => {
  const idx = buildIndex("../skills");
  const pptx = idx.skills.find((s) => s.slug === "pptx");
  assert.ok(pptx, "pptx present");
  assert.ok(!pptx.description.startsWith('"'), "no stray leading quote delimiter");
  assert.ok(!pptx.description.includes('\\"'), "internal escapes were unescaped");
  assert.ok(pptx.description.length > 0, "pptx has a description");
});

test("top-level shape", () => {
  const idx = buildIndex("../skills");
  assert.equal(idx.repo, "opcify/skills");
  assert.equal(typeof idx.version, "string");
  assert.ok(Array.isArray(idx.skills));
});
