import { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { 
  Plus, 
  Trash2, 
  Search as SearchIcon, 
  ArrowRight, 
  FileImage, 
  Coins, 
  CalendarDays, 
  Clock 
} from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export default function History() {
  const [searches, setSearches] = useState([]);
  const [config, setConfig] = useState({ programs: [], currencies: [] });
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  // URL DO BACKEND (PYTHON)
  const API_URL = 'http://localhost:5000';

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [resSearches, resConfig] = await Promise.all([
        axios.get('/api/searches'),
        axios.get('/api/config')
      ]);
      // Ordena por data de criação (mais recente primeiro)
      const sorted = resSearches.data.sort((a, b) => 
        new Date(b.created_at || b.id) - new Date(a.created_at || a.id)
      );
      setSearches(sorted);
      setConfig(resConfig.data);
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Tem certeza que deseja excluir este registro?")) return;
    
    // Atualiza a tela antes do backend responder (UI mais rápida)
    setSearches(current => current.filter(s => s.id !== id));

    try {
      await axios.delete(`/api/searches/${id}`);
    } catch (error) {
      alert("Erro ao excluir. Tente novamente.");
      fetchData(); // Reverte se der erro
    }
  };

  // --- CORREÇÃO PRINCIPAL: CACHE BUSTER ---
  const handleDownload = (id) => {
    // Gera um número aleatório para enganar o cache do navegador
    const random = Math.random();
    // Monta a URL forçando o navegador a fazer uma nova requisição
    const url = `${API_URL}/api/generate/${id}?v=${random}`;
    
    console.log("Tentando baixar imagem de:", url);
    window.open(url, '_blank');
  };

  // Função auxiliar para renderizar a lista de preços
  const renderPriceList = (pricesRaw) => {
    if (!pricesRaw) return <span className="text-slate-300">-</span>;

    let prices = [];
    try {
      prices = typeof pricesRaw === 'string' ? JSON.parse(pricesRaw) : pricesRaw;
    } catch (e) { return null; }

    if (!Array.isArray(prices) || prices.length === 0) return <span className="text-slate-300">-</span>;

    return (
      <div className="flex flex-col gap-1">
        {prices.map((p, idx) => {
          const progName = config.programs.find(prog => String(prog.id) === String(p.prog_id))?.name || 'Prog';
          const currCode = config.currencies.find(curr => String(curr.id) === String(p.curr_id))?.code || 'R$';
          
          return (
            <div key={idx} className="text-xs flex items-center gap-1.5 whitespace-nowrap">
               <span className="font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">{progName}</span>
               <span className="font-medium text-slate-600">
                 {(parseInt(p.miles) || 0).toLocaleString('pt-BR')}
               </span>
               <span className="text-slate-300 text-[10px]">+</span>
               <span className="text-slate-500 text-[10px] flex items-center">
                  {currCode} {p.tax}
               </span>
            </div>
          );
        })}
      </div>
    );
  };

  // Filtro de busca local
  const filteredSearches = searches.filter(item => 
    (item.origin || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (item.destination || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (item.operator || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex min-h-screen bg-[#F8FAFC] font-sans text-slate-900">
      <Sidebar />
      <main className="ml-64 flex-1 p-8">
        
        <div className="max-w-7xl mx-auto mb-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Gestão de Pesquisas</h1>
              <p className="text-slate-500 text-sm mt-1">Histórico completo de ofertas e custos.</p>
            </div>
            
            <Link to="/register" className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-blue-600/20 hover:scale-[1.02] transition-all">
              <Plus size={18} /> Nova Oferta
            </Link>
          </div>

          <div className="bg-white p-2 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3 w-full md:w-96">
            <SearchIcon size={20} className="text-slate-400 ml-2" />
            <input 
              type="text" 
              placeholder="Buscar..." 
              className="flex-1 outline-none text-sm h-8 bg-transparent"
              value={searchTerm} 
              onChange={(e) => setSearchTerm(e.target.value)} 
            />
          </div>
        </div>

        <div className="max-w-7xl mx-auto bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          {loading ? (
             <div className="p-12 text-center text-slate-400">Carregando registros...</div>
          ) : filteredSearches.length === 0 ? (
             <div className="p-12 text-center text-slate-400">Nenhum registro encontrado.</div>
          ) : (
            <div className="overflow-x-auto">
              {/* Tabela Limpa (Sem espaços soltos entre tags) */}
              <table className="w-full text-left border-collapse">
                <thead className="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-500 uppercase">
                  <tr>
                    <th className="px-6 py-4">Criado em</th>
                    <th className="px-6 py-4">Ref. Pesquisa</th>
                    <th className="px-6 py-4">Rota</th>
                    <th className="px-6 py-4">Cia / Classe</th>
                    <th className="px-6 py-4"><div className="flex items-center gap-1"><Coins size={14}/> Custos</div></th>
                    <th className="px-6 py-4 text-center">Opção 2?</th>
                    <th className="px-6 py-4 text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredSearches.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50 transition-colors group">
                      
                      {/* Criado em */}
                      <td className="px-6 py-4 text-xs text-slate-400 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                            <Clock size={12}/>
                            {item.created_at ? format(new Date(item.created_at), "dd/MM HH:mm") : '-'}
                        </div>
                      </td>

                      {/* Ref. Pesquisa */}
                      <td className="px-6 py-4 text-sm font-semibold text-slate-700 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                            <CalendarDays size={14} className="text-blue-500"/>
                            {item.search_date ? format(parseISO(item.search_date), "dd/MM/yyyy") : '-'}
                        </div>
                      </td>
                      
                      {/* Rota */}
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2 font-bold text-slate-700 text-sm">
                            <span className="bg-slate-100 px-2 py-1 rounded">{item.origin}</span>
                            <ArrowRight size={12} className="text-slate-300"/>
                            <span className="bg-slate-100 px-2 py-1 rounded">{item.destination}</span>
                        </div>
                      </td>

                      {/* Cia */}
                      <td className="px-6 py-4">
                         <div className="flex flex-col gap-1">
                            <span className="text-sm font-semibold text-slate-700">{item.operator}</span>
                            <span className={`w-fit px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              item.flight_type === 'Executiva' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                            }`}>
                                {item.flight_type}
                            </span>
                         </div>
                      </td>

                      {/* Custos */}
                      <td className="px-6 py-4 min-w-[200px]">
                         {renderPriceList(item.prices_1)}
                      </td>

                      {/* Opção 2 */}
                      <td className="px-6 py-4 text-center">
                          {item.origin_2 ? (
                            <div className="flex flex-col items-center">
                                <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-[10px] font-bold">SIM</span>
                            </div>
                          ) : <span className="text-slate-300">-</span>}
                      </td>

                      {/* Ações */}
                      <td className="px-6 py-4 text-right">
                          <div className="flex justify-end gap-2">
                            <button 
                              onClick={() => handleDownload(item.id)}
                              className="flex items-center gap-1.5 bg-white border border-slate-200 text-slate-600 hover:text-blue-600 hover:border-blue-300 px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm"
                              title="Baixar Imagem (Gera na hora)"
                            >
                              <FileImage size={14} />
                              Baixar
                            </button>
                            <button 
                              onClick={() => handleDelete(item.id)}
                              className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                              title="Excluir"
                            >
                              <Trash2 size={16}/>
                            </button>
                          </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}