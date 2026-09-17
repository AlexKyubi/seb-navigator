const normalizeHeader=value=>String(value??"").trim().toLowerCase().replaceAll("ё","е").replace(/\s+/g," ");
const normalizeCode=value=>String(value??"").toUpperCase().replace(/[^A-Z0-9А-ЯЁ]/g,"");
const findColumn=(headers,variants)=>{for(const parts of variants){const index=headers.findIndex(header=>parts.every(part=>header.includes(part)));if(index>=0)return index}return-1};
const parseRate=value=>{if(typeof value==="number"&&Number.isFinite(value))return value>1?value/100:value;const parsed=Number(String(value??"").replace("%","").replace(",",".").trim());return Number.isFinite(parsed)?(parsed>1?parsed/100:parsed):null};

export function parseCommissionWorkbook(buffer,{fileName="Файл комиссий",strict=true}={}){
  if(!(buffer instanceof ArrayBuffer)||buffer.byteLength<100)throw Error("Файл пустой или повреждён.");
  if(buffer.byteLength>25*1024*1024)throw Error("Файл слишком большой. Максимальный размер — 25 МБ.");
  if(!globalThis.XLSX)throw Error("Модуль чтения Excel не загрузился. Проверьте соединение и повторите попытку.");
  let workbook;
  try{workbook=XLSX.read(buffer,{type:"array",cellFormula:true,cellStyles:false})}catch{throw Error("Не удалось открыть Excel. Выберите исправный файл XLSX, XLSM или XLS.")}
  if(!workbook.SheetNames?.length)throw Error("В книге нет листов.");
  if(workbook.SheetNames.length>40)throw Error("В книге слишком много листов. Проверьте выбранный файл.");
  const rows=[],diagnostics=[];
  for(const sheetName of workbook.SheetNames){
    const grid=XLSX.utils.sheet_to_json(workbook.Sheets[sheetName],{header:1,defval:null,raw:true,blankrows:false});
    if(grid.length>100000)throw Error(`Лист «${sheetName}» содержит слишком много строк.`);
    const headerRow=grid.slice(0,40).findIndex(row=>Array.isArray(row)&&row.some(value=>normalizeHeader(value)==="comm.code"));
    if(headerRow<0)continue;
    const headers=grid[headerRow].map(normalizeHeader),codeIndex=headers.indexOf("comm.code"),belowIndex=findColumn(headers,[["ниже","план"],["ниже","100"],["<","100"]]),planIndex=findColumn(headers,[["выше","план"],["100%"],["при выполн"],[">=","100"]]);
    if(codeIndex<0||belowIndex<0||planIndex<0){diagnostics.push(`Лист «${sheetName}»: не найдены обе колонки ставок.`);continue}
    for(let index=headerRow+1;index<grid.length;index++){
      const row=grid[index],commCode=String(row?.[codeIndex]??"").trim();
      if(!commCode)continue;
      const belowPlan=parseRate(row[belowIndex]),atPlan=parseRate(row[planIndex]);
      if(belowPlan===null||atPlan===null||belowPlan<0||belowPlan>1||atPlan<0||atPlan>1)continue;
      rows.push({commCode,normalizedCode:normalizeCode(commCode),belowPlan,atPlan,sheet:sheetName,row:index+1});
    }
  }
  const uniqueCodes=new Set(rows.map(row=>row.normalizedCode).filter(Boolean));
  if(!rows.length)throw Error(diagnostics[0]||"Не найдена таблица с Comm.Code и двумя ставками комиссии.");
  if(strict&&uniqueCodes.size<3)throw Error("В файле слишком мало корректных товаров. Проверьте таблицу комиссий.");
  return{fileName,importedAt:new Date().toISOString(),rows,summary:{sheets:workbook.SheetNames.length,validRows:rows.length,uniqueCodes:uniqueCodes.size}};
}

export async function readCommissionFile(file,{strict=true}={}){
  if(!file)throw Error("Выберите Excel с комиссией.");
  if(!/\.xlsx$/i.test(file.name||""))throw Error("Нужен файл XLSX. Старые XLS и книги с макросами необходимо сохранить как XLSX.");
  const buffer=await file.arrayBuffer(),dataset=parseCommissionWorkbook(buffer,{fileName:file.name,strict});
  return{buffer,dataset:{...dataset,rawWorkbook:buffer}};
}
