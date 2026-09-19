const fs=require("fs"),path=require("path");
const root=path.resolve(__dirname,".."),dist=path.join(root,"dist"),failures=[];
const read=relative=>fs.readFileSync(path.join(dist,relative),"utf8");
const pages={"index.html":"assets/catalog.js","overview.html":"assets/overview.js","sales.html":"assets/sales.js","auth.html":"assets/auth.js"};
for(const[htmlFile,jsFile]of Object.entries(pages)){
  const html=read(htmlFile),js=read(jsFile),ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]));
  if(ids.size!==[...html.matchAll(/\bid="([^"]+)"/g)].length)failures.push(`${htmlFile}: duplicate id`);
  for(const match of js.matchAll(/\$\("([A-Za-z][\w-]*)"\)/g))if(!ids.has(match[1]))failures.push(`${jsFile}: missing #${match[1]} in ${htmlFile}`);
  for(const match of html.matchAll(/(?:src|href)="\.\/([^"?#]+)"/g))if(!fs.existsSync(path.join(dist,match[1])))failures.push(`${htmlFile}: missing ${match[1]}`);
}
const CATALOG_OBFUSCATION_KEY=Buffer.from("seb-navigator-2026-catalog-key","utf8");
function deobfuscateCatalog(base64){const bytes=Buffer.from(base64,"base64");for(let i=0;i<bytes.length;i++)bytes[i]^=CATALOG_OBFUSCATION_KEY[i%CATALOG_OBFUSCATION_KEY.length];return bytes.toString("utf8")}
const catalog=JSON.parse(deobfuscateCatalog(read("data/idx-7f2ae1.bin")));
if(!Array.isArray(catalog)||catalog.length<1)failures.push("catalog is empty");
const articles=new Set();for(const[index,item]of catalog.entries()){if(!item?.article||!item?.title)failures.push(`catalog row ${index+1}: required value missing`);if(articles.has(item.article))failures.push(`duplicate article ${item.article}`);articles.add(item.article)}
if(fs.existsSync(path.join(dist,"data/default-commissions.json")))failures.push("default commission dataset must not be public");
if(fs.existsSync(path.join(dist,"data/catalog.json")))failures.push("plain readable catalog.json must not be published (use the obfuscated file)");
const headers=read("_headers"),sw=read("sw.js"),allCode=Object.values(pages).map(read).join("\n")+read("assets/core.js")+read("assets/commission.js");
for(const required of["Content-Security-Policy","X-Content-Type-Options","X-Frame-Options","Permissions-Policy"])if(!headers.includes(required))failures.push(`missing security header ${required}`);
if(!sw.includes("Authorization required")||!sw.includes("authorized-profile"))failures.push("service worker data gate missing");
const publicAuth=read("auth.html")+read("assets/auth.js");if(/Comm\.Code|двумя ставками|колонк[аи] ставок/i.test(publicAuth))failures.push("authorization UI reveals validation criteria");
if(/\beval\s*\(|new Function\s*\(/.test(allCode))failures.push("unsafe dynamic code execution detected");
const maps=[];for(const dir of[dist,path.join(dist,"assets")])for(const name of fs.readdirSync(dir))if(name.endsWith(".map"))maps.push(name);if(maps.length)failures.push(`source maps found: ${maps.join(", ")}`);
if(failures.length){console.error(failures.join("\n"));process.exit(1)}
console.log(JSON.stringify({pages:Object.keys(pages).length,products:catalog.length,uniqueArticles:articles.size,securityHeaders:true,authorizationGate:true,sourceMaps:0}));
