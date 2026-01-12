import { useState } from 'react';
import { Plus, Trash2, Tag, CreditCard, ChevronDown, Coins } from 'lucide-react';

export default function PriceManager({ programs = [], currencies = [], onUpdate, initialData }) {
  // ATUALIZAÇÃO: Inicia com initialData se existir, senão usa array padrão vazio
  const [prices, setPrices] = useState(
    (initialData && initialData.length > 0) 
      ? initialData 
      : [{ id: Date.now(), miles: '', prog_id: '', tax: '', curr_id: '' }]
  );

  const updatePrices = (newPrices) => {
    setPrices(newPrices);
    onUpdate(newPrices);
  };

  const addRow = () => {
    const newPrices = [...prices, { id: Date.now(), miles: '', prog_id: '', tax: '', curr_id: '' }];
    updatePrices(newPrices);
  };

  const removeRow = (id) => {
    let newPrices;
    if (prices.length === 1) {
       newPrices = [{ id: Date.now(), miles: '', prog_id: '', tax: '', curr_id: '' }];
    } else {
       newPrices = prices.filter(p => p.id !== id);
    }
    updatePrices(newPrices);
  };

  const handleChange = (id, field, value) => {
    const newPrices = prices.map(p => {
      if (p.id === id) return { ...p, [field]: value };
      return p;
    });
    updatePrices(newPrices);
  };

  return (
    <div className="bg-slate-50 rounded-2xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-4">
         <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <CreditCard size={14} /> Custos (Milhas & Taxas)
         </label>
      </div>

      <div className="space-y-3">
        {prices.map((price) => (
          <div key={price.id} className="flex flex-col xl:flex-row gap-3 items-start xl:items-center bg-white p-3 rounded-xl border border-slate-200 shadow-sm transition-all hover:border-blue-200 hover:shadow-md">
            
            {/* 1. INPUT MILHAS */}
            <div className="relative flex-1 w-full xl:w-auto">
               <input 
                 type="number" 
                 placeholder="0" 
                 className="w-full pl-4 pr-16 py-2.5 text-sm font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none transition-all placeholder:font-normal placeholder:text-slate-300"
                 value={price.miles}
                 onChange={(e) => handleChange(price.id, 'miles', e.target.value)}
               />
               <span className="absolute right-3 top-2.5 text-[10px] font-bold text-slate-400 tracking-wider pointer-events-none bg-transparent">MILHAS</span>
            </div>

            {/* 2. SELECT PROGRAMA */}
            <div className="relative flex-[1.5] w-full xl:w-auto group">
               <select 
                 className="w-full pl-4 pr-10 py-2.5 text-sm font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg appearance-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none cursor-pointer transition-all"
                 value={price.prog_id}
                 onChange={(e) => handleChange(price.id, 'prog_id', e.target.value)}
               >
                 <option value="" className="text-slate-400">Selecionar Programa...</option>
                 {programs.map(p => (
                   <option key={p.id} value={p.id}>{p.name}</option>
                 ))}
               </select>
               <div className="absolute right-3 top-3 text-slate-400 pointer-events-none group-hover:text-blue-500 transition-colors">
                  <ChevronDown size={16} />
               </div>
            </div>

            <div className="text-slate-300 hidden xl:flex items-center justify-center font-light text-xl h-full pb-1">+</div>

            {/* 3. SELECT MOEDA */}
            <div className="relative w-full xl:w-32 group">
               <div className="absolute left-3 top-2.5 text-slate-400 pointer-events-none">
                  <Coins size={16} />
               </div>
               <select 
                 className="w-full pl-10 pr-8 py-2.5 text-sm font-bold text-slate-700 bg-white border border-slate-200 rounded-lg appearance-none focus:border-green-400 focus:ring-2 focus:ring-green-100 outline-none cursor-pointer transition-all"
                 value={price.curr_id}
                 onChange={(e) => handleChange(price.id, 'curr_id', e.target.value)}
               >
                 {currencies.map(c => (
                   <option key={c.id} value={c.id}>{c.code}</option>
                 ))}
                 {currencies.length === 0 && <option value="1">R$</option>}
               </select>
               <div className="absolute right-2 top-3 text-slate-400 pointer-events-none group-hover:text-green-500 transition-colors">
                  <ChevronDown size={14} />
               </div>
            </div>

            {/* 4. INPUT TAXAS */}
            <div className="relative w-full xl:w-40">
               <span className="absolute left-3 top-2.5 text-slate-400"><Tag size={16}/></span>
               <input 
                 type="number" 
                 placeholder="0,00" 
                 className="w-full pl-9 pr-4 py-2.5 text-sm font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:border-green-400 focus:ring-2 focus:ring-green-100 outline-none text-right transition-all placeholder:text-slate-300"
                 value={price.tax}
                 onChange={(e) => handleChange(price.id, 'tax', e.target.value)}
               />
            </div>

            {/* 5. REMOVER */}
            <button 
              type="button"
              onClick={() => removeRow(price.id)}
              className="p-2.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors xl:ml-2 flex items-center justify-center"
              title="Remover preço"
            >
              <Trash2 size={18} />
            </button>
          </div>
        ))}
      </div>

      <button 
        type="button"
        onClick={addRow}
        className="mt-4 w-full border border-dashed border-slate-300 hover:border-blue-300 hover:bg-blue-50 text-slate-500 hover:text-blue-600 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2"
      >
        <Plus size={16} /> Adicionar Opção de Pagamento
      </button>
    </div>
  );
}