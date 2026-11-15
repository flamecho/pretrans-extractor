const fs=require('fs'), path=require('path'), vm=require('vm');
const work=path.resolve(process.argv[2] || path.join(__dirname,'../../_work_agastar')), app=path.join(work,'app');
const warnings=[];
const context={tyrano:{plugin:{kag:{}}}, $:{trim:s=>s==null?'':String(s).trim(), replaceAll:(s,a,b)=>s.split(a).join(b)}, alert:s=>{throw Error(s)}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(app,'tyrano/plugins/kag/kag.parser.js'),'utf8'),context);
const parser=context.tyrano.plugin.kag.parser;
parser.kag={config:parser.compileConfig(fs.readFileSync(path.join(app,'data/system/Config.tjs'),'utf8')),stat:{current_scenario:''},warning:(...s)=>warnings.push(s),error:s=>{throw Error(s)},convertLang:()=>{}};
function scenarios(dir, prefix='') {
  return fs.readdirSync(dir, {withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name)).flatMap(item=>{
    const relative=prefix+item.name;
    if(item.isDirectory())return scenarios(path.join(dir,item.name),relative+'/');
    return relative.endsWith('.ks')?[relative]:[];
  });
}
const result={};
for(const scenario of scenarios(app)){
  parser.flag_script=false;parser.deep_if=0;parser.kag.stat.current_scenario=scenario;
  result[scenario]=parser.parseScenario(fs.readFileSync(path.join(app,scenario),'utf8')).array_s;
  result[scenario].forEach((t,i)=>{t._index=i});
}
fs.writeFileSync(path.join(work,'tokens.json'),JSON.stringify(result));
fs.writeFileSync(path.join(work,'parser_warnings.json'),JSON.stringify(warnings,null,2));
console.log('Native parser:',Object.keys(result).length,'scripts;',Object.values(result).reduce((a,t)=>a+t.length,0),'tokens;',warnings.length,'warnings; KeepSpaceInParameterValue=',parser.kag.config.KeepSpaceInParameterValue);
