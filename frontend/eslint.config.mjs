import { dirname, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });
const srcRoot = resolve(dirname(fileURLToPath(import.meta.url)), "src");
const routeRoot = resolve(dirname(fileURLToPath(import.meta.url)), "app");
const layers = ["app", "pages-flat", "widgets", "features", "entities", "shared"];

function checkFsdImport(context, node) {
  const specifier = node.source?.value;
  if (typeof specifier !== "string" || !(specifier.startsWith("@/") || specifier.startsWith("."))) return;

  const importer = relative(srcRoot, context.filename).split(sep);
  const routeRelative = relative(routeRoot, context.filename);
  const isRouteFile = routeRelative !== ".." && !routeRelative.startsWith(`..${sep}`);
  const targetPath = specifier.startsWith("@/")
    ? resolve(srcRoot, specifier.slice(2))
    : resolve(dirname(context.filename), specifier);
  const target = relative(srcRoot, targetPath).split(sep);
  const fromRank = layers.indexOf(importer[0]);
  const toRank = layers.indexOf(target[0]);
  if ((fromRank < 0 && !isRouteFile) || toRank < 0 || target[1] === undefined) return;
  if (isRouteFile) {
    if (target.length !== 2 && specifier !== "@/app/styles/globals.css") {
      context.report({ node, message: `FSD: route files must import ${target[0]}/${target[1]} through its public index.ts.` });
    }
    return;
  }

  const sameSlice = importer[0] === target[0] && importer[1] === target[1];
  if (sameSlice) return;
  if (toRank <= fromRank) {
    context.report({ node, message: `FSD: ${importer[0]}/${importer[1]} cannot import ${target[0]}/${target[1]}. Dependencies must point to a lower layer; sibling slices are isolated.` });
    return;
  }
  if (target.length !== 2) {
    context.report({ node, message: `FSD: import ${target[0]}/${target[1]} through its public index.ts only.` });
  }
}

const config = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts"],
  },
  {
    files: ["src/**/*.{ts,tsx}", "app/**/*.{ts,tsx}"],
    plugins: {
      fsd: {
        rules: {
          boundaries: {
            meta: { type: "problem", schema: [] },
            create(context) {
              return {
                ImportDeclaration: (node) => checkFsdImport(context, node),
                ExportNamedDeclaration: (node) => checkFsdImport(context, node),
                ExportAllDeclaration: (node) => checkFsdImport(context, node),
              };
            },
          },
        },
      },
    },
    rules: { "fsd/boundaries": "error" },
  },
];

export default config;
