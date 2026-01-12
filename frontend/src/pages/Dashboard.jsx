import { useState, useEffect } from 'react';
import axios from 'axios';
import Sidebar from '../components/Sidebar';
import { TrendingUp, Map, Briefcase, Plane, ArrowRight } from 'lucide-react';

export default function Dashboard() {
  const [stats, setStats] = useState({
    total: 0,
    topOrigins: [],
    topDestinations: [],
    topRoutes: [], // Ex: GRU -> MIA
    topOperators: []
  });

  useEffect(() => {
    async function loadStats() {
      try {
        const res = await axios.get('/api/searches');
        const data = res.data;

        // 1. Total
        const total = data.length;

        // 2. Calcular Frequências
        const routeCounts = {};
        const opCounts = {};

        data.forEach(item => {
          // Rota
          const route = `${item.origin} ➝ ${item.destination}`;
          routeCounts[route] = (routeCounts[route] || 0) + 1;

          // Operadora
          if(item.operator) {
             opCounts[item.operator] = (opCounts[item.operator] || 0) + 1;
          }
        });

        // Ordenar e pegar Top 5
        const sortedRoutes = Object.entries(routeCounts)
            .sort((a,b) => b[1] - a[1])
            .slice(0, 5);
        
        const sortedOps = Object.entries(opCounts)
            .sort((a,b) => b[1] - a[1])
            .slice(0, 5);

        setStats({ total, topRoutes: sortedRoutes, topOperators: sortedOps });

      } catch (error) {
        console.error("Erro stats:", error);
      }
    }
    loadStats();
  }, []);

  return (
    <div className="flex min-h-screen bg-[#F8FAFC] font-sans text-slate-900">
      <Sidebar />
      <main className="ml-64 flex-1 p-8">
        
        <div className="mb-8">
           <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Visão Geral</h1>
           <p className="text-slate-500 mt-1">Insights sobre as ofertas geradas no sistema.</p>
        </div>

        {/* --- KPI CARDS (Indicadores) --- */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {/* Card 1 */}
            <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
                <div className="p-4 bg-blue-50 text-blue-600 rounded-xl">
                    <TrendingUp size={24} />
                </div>
                <div>
                    <p className="text-slate-400 text-xs font-bold uppercase tracking-wider">Total de Ofertas</p>
                    <h3 className="text-3xl font-black text-slate-800">{stats.total}</h3>
                </div>
            </div>

            {/* Card 2 */}
            <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
                <div className="p-4 bg-purple-50 text-purple-600 rounded-xl">
                    <Map size={24} />
                </div>
                <div>
                    <p className="text-slate-400 text-xs font-bold uppercase tracking-wider">Rota Favorita</p>
                    <h3 className="text-xl font-bold text-slate-800 truncate max-w-[150px]">
                        {stats.topRoutes[0] ? stats.topRoutes[0][0] : '-'}
                    </h3>
                </div>
            </div>

            {/* Card 3 */}
            <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
                <div className="p-4 bg-emerald-50 text-emerald-600 rounded-xl">
                    <Briefcase size={24} />
                </div>
                <div>
                    <p className="text-slate-400 text-xs font-bold uppercase tracking-wider">Cia. Top 1</p>
                    <h3 className="text-xl font-bold text-slate-800">
                        {stats.topOperators[0] ? stats.topOperators[0][0] : '-'}
                    </h3>
                </div>
            </div>
        </div>

        {/* --- LISTAS DE RANKING --- */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            
            {/* Ranking Rotas */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                <h3 className="font-bold text-slate-700 mb-6 flex items-center gap-2">
                    <Plane size={18} className="text-blue-500"/> Rotas Mais Pesquisadas
                </h3>
                <div className="space-y-4">
                    {stats.topRoutes.map(([name, count], idx) => (
                        <div key={name} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                            <div className="flex items-center gap-3">
                                <span className="w-6 h-6 flex items-center justify-center bg-white rounded-full text-xs font-bold text-slate-400 shadow-sm border border-slate-100">
                                    {idx + 1}
                                </span>
                                <span className="font-bold text-slate-700">{name}</span>
                            </div>
                            <span className="text-xs font-bold bg-blue-100 text-blue-700 px-2 py-1 rounded-lg">
                                {count}x
                            </span>
                        </div>
                    ))}
                    {stats.topRoutes.length === 0 && <p className="text-slate-400 text-sm">Sem dados ainda.</p>}
                </div>
            </div>

            {/* Ranking Cias */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                <h3 className="font-bold text-slate-700 mb-6 flex items-center gap-2">
                    <Briefcase size={18} className="text-purple-500"/> Top Companhias Aéreas
                </h3>
                <div className="space-y-4">
                    {stats.topOperators.map(([name, count], idx) => (
                        <div key={name} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                             <div className="flex items-center gap-3">
                                <span className="w-6 h-6 flex items-center justify-center bg-white rounded-full text-xs font-bold text-slate-400 shadow-sm border border-slate-100">
                                    {idx + 1}
                                </span>
                                <span className="font-medium text-slate-700">{name}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="h-2 w-24 bg-slate-200 rounded-full overflow-hidden">
                                    <div className="h-full bg-purple-500 rounded-full" style={{ width: `${(count / stats.total) * 100}%` }}></div>
                                </div>
                                <span className="text-xs font-bold text-slate-500">{count}</span>
                            </div>
                        </div>
                    ))}
                    {stats.topOperators.length === 0 && <p className="text-slate-400 text-sm">Sem dados ainda.</p>}
                </div>
            </div>

        </div>
      </main>
    </div>
  );
}