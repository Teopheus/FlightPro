import { useState, useEffect } from 'react';
import Flatpickr from 'react-flatpickr';
import "flatpickr/dist/themes/material_blue.css";
import { Portuguese } from 'flatpickr/dist/l10n/pt';
import { Calendar, Trash2, X, Check, CalendarDays, ChevronRight, AlertCircle, FileText, ArrowRight, ToggleLeft, ToggleRight } from 'lucide-react';
import { format, parseISO, isValid } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export default function DateManager({ label, onUpdate, initialData }) {
  
  // --- FUNÇÃO PARA PROCESSAR DADOS ANTIGOS E NOVOS ---
  // Se initialData for Array (versão antiga), converte. Se for Objeto (versão nova com showSeats), usa.
  const processInitialData = (data) => {
    if (!data) return { list: [], showSeats: true };
    if (Array.isArray(data)) return { list: data, showSeats: true };
    return { list: data.list || [], showSeats: data.showSeats ?? true };
  };

  const loaded = processInitialData(initialData);

  // Estados
  const [selectedDates, setSelectedDates] = useState(loaded.list);
  const [showSeats, setShowSeats] = useState(loaded.showSeats); // Novo Estado: Controla se exibe vagas
  
  const [isOpen, setIsOpen] = useState(false);
  const [defaultSeats, setDefaultSeats] = useState(1);
  const [viewMode, setViewMode] = useState('calendar'); 
  const [importText, setImportText] = useState('');

  // Bloqueio de Scroll
  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : 'unset';
    return () => { document.body.style.overflow = 'unset'; };
  }, [isOpen]);

  // --- FORMATAÇÃO SEGURA ---
  const formatDateSafe = (dateString, formatStr) => {
    if (!dateString) return "Data Inválida";
    try {
      const date = parseISO(dateString);
      if (!isValid(date)) return "Data Inválida";
      return format(date, formatStr, { locale: ptBR });
    } catch (e) {
      return "Erro Data";
    }
  };

  // --- SINCRONIZAÇÃO (ATUALIZADA) ---
  const notifyParent = (currentList, currentShowSeats) => {
    const sorted = [...currentList].sort((a, b) => a.date.localeCompare(b.date));
    
    const monthNames = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"];
    const groups = {};
    
    sorted.forEach(item => {
      if(!item.date) return;
      const parts = item.date.split('-');
      if(parts.length !== 3) return;
      
      const [y, m, d] = parts;
      const mName = monthNames[parseInt(m) - 1];
      
      if (!groups[mName]) groups[mName] = [];
      
      // LÓGICA DE TEXTO: Se showSeats for true, põe (X). Se não, põe só o dia.
      if (currentShowSeats) {
          groups[mName].push(`${parseInt(d)}(${item.seats})`);
      } else {
          groups[mName].push(`${parseInt(d)}`);
      }
    });

    let finalStr = "";
    Object.entries(groups).forEach(([month, days]) => {
      finalStr += `${month}: ${days.join(', ')}\n`;
    });
    
    // ATENÇÃO: Agora salvamos um OBJETO no raw data, contendo a lista e a preferência
    onUpdate(finalStr.trim(), { list: sorted, showSeats: currentShowSeats });
  };

  // Wrapper para atualizar estado e notificar
  const handleUpdate = (newList, newShowSeats) => {
      setSelectedDates(newList);
      setShowSeats(newShowSeats);
      notifyParent(newList, newShowSeats);
  };

  // --- IMPORTAÇÃO ---
  const handleImport = () => {
    const lines = importText.split('\n');
    let importedCount = 0;
    const newItems = [...selectedDates]; 

    lines.forEach(line => {
      const parts = line.trim().split(/\t+| {2,}/);
      if (parts.length > 0) {
        const dateRaw = parts[0].trim();
        if (dateRaw.match(/^\d{1,2}\/\d{1,2}\/\d{4}$/)) {
          const [d, m, y] = dateRaw.split('/');
          const iso = `${y}-${m.padStart(2,'0')}-${d.padStart(2,'0')}`;
          const seats = parts[1] ? parseInt(parts[1]) : defaultSeats;

          const existsIndex = newItems.findIndex(i => i.date === iso);
          if (existsIndex >= 0) newItems[existsIndex].seats = seats;
          else newItems.push({ date: iso, seats });
          
          importedCount++;
        }
      }
    });

    if (importedCount > 0) {
      handleUpdate(newItems, showSeats);
      setImportText('');
      alert(`${importedCount} datas importadas!`);
    } else {
      alert("Nenhuma data válida encontrada.");
    }
  };

  // --- CALENDÁRIO ---
  const handleCalendarChange = (dates) => {
    const pickedDatesStr = dates.map(date => {
        try {
            const offset = date.getTimezoneOffset();
            const adjusted = new Date(date.getTime() - (offset * 60 * 1000));
            return adjusted.toISOString().split('T')[0];
        } catch (e) { return null; }
    }).filter(d => d !== null);

    const newSelection = [];
    pickedDatesStr.forEach(dateStr => {
      const existing = selectedDates.find(d => d.date === dateStr);
      if (existing) newSelection.push(existing);
      else newSelection.push({ date: dateStr, seats: defaultSeats });
    });

    handleUpdate(newSelection, showSeats);
  };

  const updateSeats = (dateStr, newVal) => {
    const updated = selectedDates.map(d => d.date === dateStr ? { ...d, seats: newVal } : d);
    handleUpdate(updated, showSeats);
  };

  const removeDate = (dateStr) => {
    const updated = selectedDates.filter(d => d.date !== dateStr);
    handleUpdate(updated, showSeats);
  };

  // Toggle de Exibir Vagas
  const toggleShowSeats = () => {
      handleUpdate(selectedDates, !showSeats);
  };

  const getSummaryText = () => {
    if (selectedDates.length === 0) return "Selecionar datas...";
    if (selectedDates.length === 1) return "1 data selecionada";
    return `${selectedDates.length} datas selecionadas`;
  };

  return (
    <>
      <style>{`
        .flatpickr-calendar {
            box-shadow: none !important;
            border: none !important;
            width: fit-content !important;
            margin: 0 auto !important;
        }
        .flatpickr-months {
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }
        .flatpickr-months .flatpickr-month {
            height: 50px !important;
            padding-top: 10px !important;
        }
        .flatpickr-current-month {
            padding-top: 0 !important;
            height: 100% !important;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .flatpickr-innerContainer {
            border: 1px solid #e2e8f0;
            border-top: none;
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
        }
        .flatpickr-input { display: none !important; }
      `}</style>

      {/* GATILHO */}
      <div
        onClick={() => setIsOpen(true)}
        className="w-full cursor-pointer bg-white border border-slate-200 rounded-xl px-4 py-3 flex items-center justify-between transition-all hover:border-blue-400 hover:shadow-sm hover:bg-blue-50/30 group"
      >
        <div className="flex items-center gap-3 w-full overflow-hidden">
            <div className={`p-2 rounded-lg transition-colors shrink-0 ${selectedDates.length > 0 ? 'bg-blue-600 text-white shadow-blue-200' : 'bg-slate-100 text-slate-400 group-hover:bg-white group-hover:text-blue-500'}`}>
                <CalendarDays size={20} />
            </div>
            <div className="flex flex-col truncate">
                <span className="text-[10px] font-bold text-slate-400 uppercase leading-none mb-1 group-hover:text-blue-400 transition-colors">{label || "Disponibilidade"}</span>
                <span className={`text-sm font-bold truncate ${selectedDates.length > 0 ? 'text-blue-700' : 'text-slate-500'}`}>
                  {getSummaryText()}
                </span>
            </div>
        </div>
        <div className="text-slate-300 group-hover:text-blue-500 transition-colors">
           <ChevronRight size={18} />
        </div>
      </div>

      {/* MODAL */}
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl h-[85vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200 border border-slate-200">
            
            {/* Header */}
            <div className="bg-white border-b border-slate-100 px-6 py-4 flex justify-between items-center shrink-0">
                <div>
                   <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                     <Calendar className="text-blue-600" size={20}/> Gerenciar Datas
                   </h3>
                </div>
                <button onClick={() => setIsOpen(false)} className="p-2 hover:bg-slate-100 rounded-full text-slate-400 hover:text-slate-600 transition-colors">
                    <X size={24} />
                </button>
            </div>

            {/* CORPO */}
            <div className="flex-1 flex flex-col md:flex-row overflow-hidden bg-slate-50/50">
                
                {/* COLUNA ESQUERDA */}
                <div className="flex-1 p-6 flex flex-col overflow-y-auto border-b md:border-b-0 md:border-r border-slate-200 custom-scrollbar">
                    
                    {/* Abas */}
                    <div className="flex bg-slate-200/50 p-1 rounded-xl mb-6 shrink-0">
                        <button onClick={() => setViewMode('calendar')} className={`flex-1 py-2 text-sm font-bold rounded-lg flex items-center justify-center gap-2 transition-all ${viewMode === 'calendar' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
                            <CalendarDays size={16} /> Calendário
                        </button>
                        <button onClick={() => setViewMode('import')} className={`flex-1 py-2 text-sm font-bold rounded-lg flex items-center justify-center gap-2 transition-all ${viewMode === 'import' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
                            <FileText size={16} /> Colar Texto
                        </button>
                    </div>

                    <div className="flex-1 flex flex-col items-center w-full">
                        {viewMode === 'calendar' ? (
                            <>
                                {/* Controle de Vagas Padrão (Só aparece se showSeats estiver ativado) */}
                                {showSeats && (
                                    <div className="mb-6 w-full max-w-sm bg-blue-50 p-3 rounded-xl border border-blue-100 flex items-center gap-3 shadow-sm animate-in slide-in-from-top-2 duration-300">
                                        <div className="bg-white p-2 rounded-lg text-blue-600 shadow-sm">
                                            <AlertCircle size={20} />
                                        </div>
                                        <div className="flex-1">
                                            <label className="text-[10px] font-bold text-blue-400 uppercase block">Vagas Padrão</label>
                                            <p className="text-xs text-blue-700 leading-tight">Ao clicar no dia, insere:</p>
                                        </div>
                                        <input
                                            type="number" min="1" value={defaultSeats}
                                            onChange={(e) => setDefaultSeats(parseInt(e.target.value) || 1)}
                                            className="w-14 h-10 text-center font-bold text-lg text-blue-700 bg-white border border-blue-200 rounded-lg focus:ring-2 focus:ring-blue-400 outline-none"
                                        />
                                    </div>
                                )}
                                
                                <div className="w-full flex justify-center">
                                    <Flatpickr
                                        className="hidden" 
                                        options={{ mode: "multiple", locale: Portuguese, dateFormat: "Y-m-d", inline: true }}
                                        value={selectedDates.map(d => d.date)}
                                        onChange={handleCalendarChange}
                                    />
                                </div>
                            </>
                        ) : (
                            <div className="w-full flex flex-col h-full">
                                <div className="bg-white p-4 rounded-xl border border-slate-200 mb-4 shadow-sm">
                                    <p className="text-xs text-slate-500 mb-2 font-medium">Cole aqui sua lista de datas.</p>
                                    <textarea
                                        className="w-full h-48 p-3 bg-slate-50 border border-slate-200 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-100 outline-none resize-none"
                                        placeholder={`15/05/2026\n20/05/2026 2`}
                                        value={importText}
                                        onChange={(e) => setImportText(e.target.value)}
                                    ></textarea>
                                </div>
                                <button onClick={handleImport} className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-xl font-bold transition-all flex justify-center items-center gap-2 shadow-lg shadow-blue-500/20">
                                    <ArrowRight size={18} /> Processar Dados
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* COLUNA DIREITA */}
                <div className="w-full md:w-80 bg-white flex flex-col shadow-inner">
                    {/* Header da Lista com Toggle */}
                    <div className="p-4 border-b border-slate-100 bg-slate-50 flex flex-col gap-3">
                        <div className="flex items-center justify-between">
                            <h4 className="font-bold text-slate-700 text-sm uppercase tracking-wide flex items-center gap-2">
                               <Check size={16} className="text-green-500"/> Lista ({selectedDates.length})
                            </h4>
                        </div>
                        
                        {/* NOVO TOGGLE: Exibir Vagas */}
                        <div 
                            onClick={toggleShowSeats}
                            className={`flex items-center justify-between p-2 rounded-lg border cursor-pointer transition-all ${showSeats ? 'bg-blue-50 border-blue-200' : 'bg-white border-slate-200 hover:border-slate-300'}`}
                        >
                            <span className="text-xs font-bold text-slate-600">Exibir nº de Vagas?</span>
                            <div className={`transition-colors ${showSeats ? 'text-blue-600' : 'text-slate-300'}`}>
                                {showSeats ? <ToggleRight size={28} /> : <ToggleLeft size={28} />}
                            </div>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                        {selectedDates.length === 0 ? (
                            <div className="text-center py-10 opacity-50">
                                <CalendarDays size={48} className="mx-auto mb-2 text-slate-300"/>
                                <p className="text-sm text-slate-400">Nenhuma data selecionada.</p>
                            </div>
                        ) : (
                            selectedDates
                            .sort((a, b) => a.date.localeCompare(b.date))
                            .map((item) => (
                                <div key={item.date} className="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-xl shadow-sm hover:border-blue-300 transition-all">
                                    <div>
                                        <div className="text-xs font-bold text-slate-400 uppercase">
                                            {formatDateSafe(item.date, 'EEE')}
                                        </div>
                                        <div className="font-bold text-slate-700 text-lg">
                                            {formatDateSafe(item.date, 'dd/MM')}
                                        </div>
                                    </div>
                                    
                                    <div className="flex items-center gap-3">
                                        {/* Só mostra input de vagas se showSeats = true */}
                                        {showSeats && (
                                            <div className="flex flex-col items-end animate-in fade-in duration-300">
                                                <label className="text-[9px] font-bold text-slate-400 uppercase">Vagas</label>
                                                <input
                                                    type="number" min="1" value={item.seats}
                                                    onChange={(e) => updateSeats(item.date, parseInt(e.target.value) || 1)}
                                                    className="w-10 text-center border-b border-slate-300 focus:border-blue-500 font-bold text-slate-700 outline-none bg-transparent h-6"
                                                />
                                            </div>
                                        )}
                                        <button onClick={() => removeDate(item.date)} className="p-2 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors">
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="bg-white p-4 border-t border-slate-200 flex justify-end gap-3 shrink-0">
                <button onClick={() => handleUpdate([], showSeats)} className="px-4 py-2 text-slate-500 hover:text-red-500 hover:bg-red-50 rounded-lg text-sm font-bold transition-colors" disabled={selectedDates.length === 0}>
                    Limpar Tudo
                </button>
                <button onClick={() => setIsOpen(false)} className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-2.5 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20 transition-all hover:scale-[1.02]">
                    <Check size={18} /> Confirmar
                </button>
            </div>

          </div>
        </div>
      )}
    </>
  );
}