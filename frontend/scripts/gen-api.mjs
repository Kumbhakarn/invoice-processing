import { access } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import openapiTS, { astToString } from 'openapi-typescript';

const input = process.argv[2] ?? process.env.OPENAPI_SCHEMA ?? 'http://127.0.0.1:8000/openapi.json';
const schema = /^https?:\/\//.test(input) ? input : pathToFileURL(resolve(input)).href;
if (schema.startsWith('file:')) await access(new URL(schema));
const ast = await openapiTS(schema);
await import('node:fs/promises').then(({ writeFile }) => writeFile(resolve('src/api/generated.ts'), astToString(ast)));
console.log(`Generated src/api/generated.ts from ${schema}`);
