/* Bakes the exported review dataset into the frontend for the static demo
   (GitHub Pages). Runs automatically before `npm run build`. */
import { copyFileSync, existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const src = join(root, 'data', 'reviews_export.json')
const destDir = join(root, 'frontend', 'src', 'data')
const dest = join(destDir, 'reviews.json')

mkdirSync(destDir, { recursive: true })
if (existsSync(src)) {
  copyFileSync(src, dest)
  console.log(`demo data baked: ${src} -> ${dest}`)
} else {
  writeFileSync(dest, '[]')
  console.log('no data/reviews_export.json found — baked an empty demo dataset')
}
