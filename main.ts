// Entry point for the post-tiktok bounty (Node 22, standard library only).
// The entry is the video itself: this program only carries VIDEO.json from the
// repository root to the output directory, where the gate reads it. The video
// was made and posted separately; VIDEO.json names its TikTok address.
//
// Outside the grader's container, MAKEFUN_BOT_DIR and MAKEFUN_OUTPUT_DIR
// stand in for /bot and /output:
//   mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts

import { copyFileSync, mkdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const BOT_DIR = process.env.MAKEFUN_BOT_DIR ?? '/bot';
const OUTPUT_DIR = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';

const SOURCE = join(BOT_DIR, 'VIDEO.json');
const TARGET = join(OUTPUT_DIR, 'VIDEO.json');

mkdirSync(OUTPUT_DIR, { recursive: true });

try {
  copyFileSync(SOURCE, TARGET);
} catch (err) {
  console.error(`VIDEO.json could not be copied from ${SOURCE}: ${(err as Error).message}`);
  process.exit(1);
}

// Read-back self-check: a copy that differs from the source must fail loudly
// instead of handing the gate a wrong VIDEO.json.
const sourceBytes = readFileSync(SOURCE);
const targetBytes = readFileSync(TARGET);
if (!sourceBytes.equals(targetBytes)) {
  console.error(`VIDEO.json copy mismatch: ${TARGET} differs from ${SOURCE}`);
  process.exit(1);
}

console.log(`VIDEO.json copied to ${TARGET} (${targetBytes.length} bytes, verified)`);
