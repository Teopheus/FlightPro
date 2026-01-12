import { useState, useEffect } from 'react';
import axios from 'axios';
import Sidebar from '../components/Sidebar';
import { Settings, Plus, Trash2, Award, Coins } from 'lucide-react';

export default function Config() {
  const [programs, setPrograms] = useState([]);
  const [currencies, setCurrencies] = useState([]);
  
  const [newProgram, setNewProgram] = useState('');
  const [newCurrency, setNewCurrency] = useState('');
  const [loading, setLoading] = useState(false);

  // Carregar dados iniciais
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const res = await axios.get('/api/config');
      setPrograms(res.data.programs);
      setCurrencies(res.data.currencies);
    } catch (error) {
      console.error("Erro ao carregar dados", error);
    }
  };

  // --- PROGRAMAS ---
  const handleAddProgram = async (e) => {
    e.preventDefault();
    if (!newProgram) return;
    setLoading(true);
    try {
      await axios.post('/api/programs', { name: newProgram });
      setNewProgram('');
      fetchData(); // Recarrega a lista
    } catch (error) {
      alert("Erro ao adicionar programa");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProgram = async (id) => {
    if (!confirm("Tem certeza que deseja remover este programa?")) return;
    try {
      await axios.delete(`/api/programs/${id}`);
      fetchData();
    } catch (error) {
      alert("Erro ao remover");
    }
  };

  // --- MOEDAS ---
  const handleAddCurrency = async (e) => {
    e.preventDefault();
    if (!newCurrency) return;
    setLoading(true);
    try {
      await axios.post('/api/currencies', { code: newCurrency });
      setNewCurrency('');
      fetchData();
    } catch (error) {
      alert("Erro ao adicionar moeda");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCurrency = async (id) => {
    if (!confirm("Tem certeza que deseja remover esta moeda?")) return;
    try {
      await axios.delete(`/api/currencies/${id}`);
      fetchData();
    } catch (error) {
      alert("Erro ao remover");
    }
  };

  return (
    <div className="flex min-h-screen bg-[#F8FAFC] font-sans text-slate-900">
      <Sidebar />
      <main className="ml-64 flex-1 p-8">
        
        {/* Cabeçalho */}
        <div className="max-w-5xl mx-auto mb-8">
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight flex items-center gap-2">
            <Settings className="text-blue-600" /> Configurações
          </h1>
          <p className="text-slate-500 text-sm mt-1">Gerencie os programas de fidelidade e moedas disponíveis para as ofertas.</p>
        </div>

        <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
            
            {/* CARD 1: PROGRAMAS */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                <div className="bg-slate-50 px-6 py-4 border-b border-slate-100 flex items-center gap-2">
                    <div className="p-1.5 bg-blue-100 text-blue-600 rounded-lg">
                        <Award size={18} />
                    </div>
                    <h3 className="font-bold text-slate-700 text-sm uppercase tracking-wide">Programas de Fidelidade</h3>
                </div>
                
                <div className="p-6">
                    {/* Form de Adição */}
                    <form onSubmit={handleAddProgram} className="flex gap-2 mb-6">
                        <input 
                            type="text" 
                            className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all"
                            placeholder="Nome do Programa (Ex: Latam Pass)"
                            value={newProgram}
                            onChange={(e) => setNewProgram(e.target.value)}
                            disabled={loading}
                        />
                        <button 
                            type="submit" 
                            disabled={loading || !newProgram}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl flex items-center justify-center transition-colors disabled:opacity-50"
                        >
                            <Plus size={20} />
                        </button>
                    </form>

                    {/* Lista */}
                    <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                        {programs.map(p => (
                            <div key={p.id} className="flex items-center justify-between p-3 bg-white border border-slate-100 rounded-xl hover:border-slate-300 hover:shadow-sm transition-all group">
                                <span className="font-medium text-slate-700">{p.name}</span>
                                <button 
                                    onClick={() => handleDeleteProgram(p.id)}
                                    className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        ))}
                        {programs.length === 0 && (
                            <p className="text-center text-slate-400 text-sm py-4">Nenhum programa cadastrado.</p>
                        )}
                    </div>
                </div>
            </div>

            {/* CARD 2: MOEDAS */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                <div className="bg-slate-50 px-6 py-4 border-b border-slate-100 flex items-center gap-2">
                    <div className="p-1.5 bg-green-100 text-green-600 rounded-lg">
                        <Coins size={18} />
                    </div>
                    <h3 className="font-bold text-slate-700 text-sm uppercase tracking-wide">Moedas & Taxas</h3>
                </div>
                
                <div className="p-6">
                    {/* Form de Adição */}
                    <form onSubmit={handleAddCurrency} className="flex gap-2 mb-6">
                        <input 
                            type="text" 
                            className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-green-100 focus:border-green-300 transition-all uppercase"
                            placeholder="Sigla (Ex: USD)"
                            value={newCurrency}
                            onChange={(e) => setNewCurrency(e.target.value)}
                            maxLength={5}
                            disabled={loading}
                        />
                        <button 
                            type="submit" 
                            disabled={loading || !newCurrency}
                            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-xl flex items-center justify-center transition-colors disabled:opacity-50"
                        >
                            <Plus size={20} />
                        </button>
                    </form>

                    {/* Lista */}
                    <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                        {currencies.map(c => (
                            <div key={c.id} className="flex items-center justify-between p-3 bg-white border border-slate-100 rounded-xl hover:border-slate-300 hover:shadow-sm transition-all group">
                                <span className="font-bold text-slate-700">{c.code}</span>
                                <button 
                                    onClick={() => handleDeleteCurrency(c.id)}
                                    className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        ))}
                         {currencies.length === 0 && (
                            <p className="text-center text-slate-400 text-sm py-4">Nenhuma moeda cadastrada.</p>
                        )}
                    </div>
                </div>
            </div>

        </div>
      </main>
    </div>
  );
}