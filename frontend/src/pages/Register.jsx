import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import DateManager from '../components/DateManager';
import PriceManager from '../components/PriceManager';
import { Save, ArrowRight, Plane, Layers, ChevronDown, PlusCircle } from 'lucide-react';

export default function Register() {
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState({
    origin: '', destination: '', operator: '', flight_type: 'Executiva',
    search_date: new Date().toISOString().split('T')[0],
    selected_bg: '', // Começa vazio e o usuário seleciona ou pegamos o primeiro
    dates_1: '', dates_2: '', 
    origin_2: '', destination_2: '',
    prices_1: [],
    prices_2: []
  });

  const [config, setConfig] = useState({ templates: [], programs: [], currencies: [] });
  const [loading, setLoading] = useState(false);
  const [showOption2, setShowOption2] = useState(false);

  useEffect(() => {
    axios.get('/api/config')
      .then(res => {
        setConfig(res.data);
        // Se houver templates e nenhum estiver selecionado, seleciona o primeiro automaticamente
        if (res.data.templates && res.data.templates.length > 0) {
            setFormData(prev => ({ ...prev, selected_bg: res.data.templates[0] }));
        }
      })
      .catch(err => console.error("Erro configs:", err));
  }, []);

  const handleChange = (e) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  // Funções de atualização memorizadas para evitar loop
  const handleDates1 = useCallback((val) => {
    setFormData(prev => (prev.dates_1 === val ? prev : { ...prev, dates_1: val }));
  }, []);

  const handleDates2 = useCallback((val) => {
    setFormData(prev => (prev.dates_2 === val ? prev : { ...prev, dates_2: val }));
  }, []);

  const handlePrices1 = useCallback((val) => {
    setFormData(prev => {
       if (prev.prices_1 === val) return prev; 
       return { ...prev, prices_1: val };
    });
  }, []);

  const handlePrices2 = useCallback((val) => {
    setFormData(prev => {
       if (prev.prices_2 === val) return prev;
       return { ...prev, prices_2: val };
    });
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post('/api/searches', formData);
      navigate('/dashboard');
    } catch (error) {
      console.error("Erro:", error);
      alert("Erro ao salvar oferta.");
    } finally {
      setLoading(false);
    }
  };

  // Função auxiliar para formatar o nome do arquivo (ex: "executiva_milhas.png" -> "Executiva Milhas")
  const formatTemplateName = (filename) => {
    return filename
      .replace('.png', '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase()); // Capitaliza primeira letra de cada palavra
  };

  return (
    <div className="flex min-h-screen bg-[#F8FAFC] font-sans text-slate-900">
      <Sidebar />
      <main className="ml-64 flex-1 p-8 pb-32">
        
        {/* Topo */}
        <div className="max-w-5xl mx-auto mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Nova Oferta</h1>
            <p className="text-slate-500 text-sm mt-1">Preencha os dados de voo, disponibilidade e custos.</p>
          </div>
          
          <div className="flex items-center gap-3 bg-white pl-4 pr-2 py-1.5 rounded-lg shadow-sm border border-slate-200">
            <div className="flex items-center gap-2 text-slate-400">
                <Layers size={14} />
                <span className="text-[10px] font-bold uppercase tracking-wider">Template</span>
            </div>
            <div className="h-4 w-px bg-slate-100"></div>
            
            {/* SELECT DE TEMPLATES CORRIGIDO */}
            <select 
                name="selected_bg" 
                className="bg-transparent text-sm font-semibold text-blue-700 outline-none cursor-pointer py-1 pr-2 min-w-[150px]"
                onChange={handleChange}
                value={formData.selected_bg}
            >
                {/* Removido a opção "Padrão (Azul)" fixa */}
                {config.templates.map(t => (
                  <option key={t} value={t}>{formatTemplateName(t)}</option>
                ))}
            </select>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="max-w-5xl mx-auto space-y-6">
          
            {/* --- CARD 1: VOO PRINCIPAL --- */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 relative z-30"> 
                <div className="bg-slate-50/50 px-6 py-3 border-b border-slate-100 flex items-center gap-2 rounded-t-2xl">
                    <div className="text-blue-600"><Plane size={16} /></div>
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Opção 1 (Principal)</span>
                </div>

                <div className="p-6 space-y-8">
                    {/* Linha 1: Rota */}
                    <div className="flex flex-col sm:flex-row gap-4 items-center">
                        <div className="flex-1 w-full">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">Origem</label>
                            <input name="origin" required onChange={handleChange} className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-center text-xl font-black text-slate-800 uppercase outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all placeholder:text-slate-300" placeholder="GRU" maxLength={3} />
                        </div>
                        <div className="text-slate-300 pt-5"><ArrowRight size={24} /></div>
                        <div className="flex-1 w-full">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">Destino</label>
                            <input name="destination" required onChange={handleChange} className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-center text-xl font-black text-slate-800 uppercase outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all placeholder:text-slate-300" placeholder="MIA" maxLength={3} />
                        </div>
                    </div>

                    {/* Linha 2: Detalhes */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">Companhia</label>
                            <input name="operator" onChange={handleChange} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm font-semibold text-slate-700 outline-none focus:ring-2 focus:ring-blue-100 transition-all" placeholder="Ex: Latam" />
                        </div>
                        <div>
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">Classe</label>
                            <select name="flight_type" onChange={handleChange} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm font-semibold text-slate-700 outline-none focus:ring-2 focus:ring-blue-100 transition-all cursor-pointer">
                                <option>Executiva</option>
                                <option>Econômica</option>
                                <option>Primeira Classe</option>
                            </select>
                        </div>
                        <div className="relative z-40"> 
                             <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">Disponibilidade</label>
                             <DateManager label="Datas de Ida" onUpdate={handleDates1} />
                        </div>
                    </div>

                    {/* Linha 3: PREÇOS */}
                    <div>
                        <PriceManager 
                          programs={config.programs} 
                          currencies={config.currencies} 
                          onUpdate={handlePrices1} 
                        />
                    </div>
                </div>
            </div>

            {/* --- CARD 2: OPÇÃO 2 --- */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 relative z-20">
                <button 
                    type="button"
                    onClick={() => setShowOption2(!showOption2)}
                    className="w-full flex items-center justify-between p-4 bg-white hover:bg-slate-50 transition-colors text-left group rounded-t-2xl"
                >
                    <div className="flex items-center gap-3">
                        <div className={`p-1.5 rounded-lg transition-colors ${showOption2 ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-400 group-hover:text-slate-600'}`}>
                            {showOption2 ? <ChevronDown size={18}/> : <PlusCircle size={18}/>}
                        </div>
                        <div>
                            <h3 className="font-bold text-slate-600 text-xs uppercase tracking-wide">Adicionar Opção 2 (Opcional)</h3>
                        </div>
                    </div>
                </button>

                {showOption2 && (
                    <div className="p-6 border-t border-slate-100 bg-slate-50/30 rounded-b-2xl space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                            <div className="md:col-span-3">
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">Origem Alt.</label>
                                <input name="origin_2" onChange={handleChange} className="w-full bg-white border border-slate-200 rounded-xl p-2.5 text-center font-bold text-slate-700 uppercase outline-none focus:border-blue-300" placeholder="MIA" maxLength={3} />
                            </div>
                            <div className="md:col-span-1 flex items-center justify-center pt-6 text-slate-300"><ArrowRight size={18} /></div>
                            <div className="md:col-span-3">
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">Destino Alt.</label>
                                <input name="destination_2" onChange={handleChange} className="w-full bg-white border border-slate-200 rounded-xl p-2.5 text-center font-bold text-slate-700 uppercase outline-none focus:border-blue-300" placeholder="GRU" maxLength={3} />
                            </div>
                            <div className="md:col-span-5 relative z-50">
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">Datas da Volta</label>
                                <DateManager label="Selecionar Datas" onUpdate={handleDates2} />
                            </div>
                        </div>

                        <div>
                            <PriceManager 
                              programs={config.programs} 
                              currencies={config.currencies} 
                              onUpdate={handlePrices2}
                            />
                        </div>
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="fixed bottom-0 left-64 right-0 bg-white/80 backdrop-blur-md border-t border-slate-200 p-4 px-8 flex justify-end gap-3 z-[60]">
                <button type="button" onClick={() => navigate('/dashboard')} className="px-6 py-2.5 rounded-lg text-slate-500 font-bold hover:bg-slate-100 transition-colors text-sm">Cancelar</button>
                <button type="submit" disabled={loading} className="px-8 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-lg shadow-blue-500/20 hover:shadow-blue-500/40 transition-all flex items-center gap-2 text-sm disabled:opacity-70 transform active:scale-95">
                    {loading ? 'Salvando...' : <><Save size={18} /> Criar Oferta</>}
                </button>
            </div>

        </form>
      </main>
    </div>
  );
}