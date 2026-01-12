import { useState, useEffect } from 'react';
import Flatpickr from 'react-flatpickr';
import "flatpickr/dist/themes/material_blue.css"; 
import { Portuguese } from 'flatpickr/dist/l10n/pt.js';
import { Calendar, List, FileSpreadsheet, Trash2, X, Check, CalendarDays } from 'lucide-react';
import { format, parseISO } from 'date-fns';

export default function DateManager({ label, onUpdate, initialData }) {
  const [selectedDates, setSelectedDates] = useState([]);
  const [isOpen, setIsOpen] = useState(false); 
  const [activeTab, setActiveTab] = useState('calendar');
  const [defaultSeats, setDefaultSeats] = useState(1);
  const [importText, setImportText] = useState('');

  // --- FUNÇÃO AUXILIAR PARA GERAR A STRING E AVISAR O PAI ---
  const notifyParent = (currentDates) => {
    const monthNames = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"];
    const groups = {};
    
    currentDates.forEach(item => {
      const [y, m, d] = item.date.split('-');
      const mName = monthNames[parseInt(m) - 1];
      if (!groups[mName]) groups[mName] = [];
      groups[mName].push(`${parseInt(d)}(${item.seats})`);
    });

    let finalStr = "";
    Object.entries(groups).forEach(([month, days]) => {
      finalStr += `${month}: ${days.join(', ')}\n`;
    });
    
    // Chama o onUpdate APENAS aqui, explicitamente
    onUpdate(finalStr.trim());
  };
  // -----------------------------------------------------------

  // Bloqueia Scroll no Modal
  useEffect(() => {
    if (isOpen) document.body.style.overflow = 'hidden';
    else document.body.style.overflow = 'unset';
    return () => { document.body.style.overflow = 'unset'; };
  }, [isOpen]);

  const handleCalendarChange = (dates) => {
    const newDates = dates.map(date => {
      const offset = date.getTimezoneOffset();
      const adjustedDate = new Date(date.getTime() - (offset * 60 * 1000));
      return adjustedDate.toISOString().split('T')[0];
    });

    // Lógica para mesclar datas
    const updatedList = [...selectedDates];
    
    newDates.forEach(dateStr => {
      if (!updatedList.find(e => e.date === dateStr)) {
        updatedList.push({ date: dateStr, seats: defaultSeats });
      }
    });
    
    // Filtra para manter apenas os que ainda estão selecionados ou já estavam
    // (A lógica do Flatpickr é complexa, aqui simplificamos: Adiciona novos, mantém velhos se existirem no input)
    // Na verdade, para simplificar UX: vamos ADICIONAR os clicados à lista existente
    
    const uniqueList = updatedList.sort((a, b) => a.date.localeCompare(b.date));
    
    setSelectedDates(uniqueList);
    notifyParent(uniqueList); // <--- AVISAR O PAI AGORA
  };

  const updateSeats = (idx, val) => {
    const newList = [...selectedDates];
    newList[idx].seats = val;
    setSelectedDates(newList);
    notifyParent(newList); // <--- AVISAR O PAI AGORA
  };

  const removeDate = (idx) => {
    const newList = selectedDates.filter((_, i) => i !== idx);
    setSelectedDates(newList);
    notifyParent(newList); // <--- AVISAR O PAI AGORA
  };

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
          const seats = parts[1] ? parseInt(parts[1]) : 1;

          const existsIndex = newItems.findIndex(i => i.date === iso);
          if (existsIndex >= 0) newItems[existsIndex].seats = seats;
          else newItems.push({ date: iso, seats });
          
          importedCount++;
        }
      }
    });

    if (importedCount > 0) {
      newItems.sort((a, b) => a.date.localeCompare(b.date));
      setSelectedDates(newItems);
      notifyParent(newItems); // <--- AVISAR O PAI AGORA
      setImportText('');
      setActiveTab('list');
      alert(`${importedCount} datas importadas!`);
    } else {
      alert("Formato inválido.");
    }
  };

  const getSummaryText = () => {
    if (selectedDates.length === 0) return "Nenhuma data selecionada";
    if (selectedDates.length === 1) return "1 data selecionada";
    return `${selectedDates.length} datas selecionadas`;
  };

  return (
    <>
      {/* GATILHO */}
      <div 
        onClick={() => setIsOpen(true)}
        className="w-full cursor-pointer bg-white border border-slate-200 rounded-xl px-4 py-3 flex items-center justify-between transition-all hover:border-blue-300 hover:bg-slate-50 group"
      >
        <div className="flex items-center gap-3 w-full overflow-hidden">
            <div className={`p-2 rounded-lg transition-colors shrink-0 ${selectedDates.length > 0 ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-400 group-hover:bg-slate-200'}`}>
                <CalendarDays size={18} />
            </div>
            <div className="truncate">
                {selectedDates.length === 0 ? (
                   <span className="text-slate-400 text-sm font-medium">Selecionar datas...</span>
                ) : (
                   <div className="flex flex-col">
                      <span className="text-[10px] font-bold text-slate-400 uppercase leading-none mb-1">Selecionado:</span>
                      <span className="text-sm font-bold text-slate-700 truncate">{getSummaryText()}</span>
                   </div>
                )}
            </div>
        </div>
      </div>

      {/* MODAL */}
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl overflow-hidden animate-in zoom-in-95 duration-200 flex flex-col max-h-[90vh]">
            
            {/* Header */}
            <div className="bg-slate-50 border-b border-slate-100 px-6 py-4 flex justify-between items-center shrink-0">
                <div className="flex items-center gap-2">
                   <Calendar className="text-blue-600" size={20}/>
                   <h3 className="font-bold text-slate-700">Gerenciar Disponibilidade</h3>
                </div>
                <button onClick={() => setIsOpen(false)} className="p-2 hover:bg-slate-200 rounded-full text-slate-400 hover:text-slate-600 transition-colors">
                    <X size={20} />
                </button>
            </div>

            {/* Tabs */}
            <div className="px-6 pt-2 border-b border-slate-100 shrink-0">
                <div className="flex gap-1">
                    <TabButton active={activeTab === 'calendar'} onClick={() => setActiveTab('calendar')} icon={Calendar} label="Calendário" />
                    <TabButton active={activeTab === 'list'} onClick={() => setActiveTab('list')} icon={List} label={`Lista (${selectedDates.length})`} />
                    <TabButton active={activeTab === 'import'} onClick={() => setActiveTab('import')} icon={FileSpreadsheet} label="Importar Excel" />
                </div>
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto">
                {activeTab === 'calendar' && (
                <div className="flex flex-col md:flex-row gap-8 items-start justify-center">
                    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm inline-block mx-auto md:mx-0">
                         <div className="flatpickr-center-fix"> 
                            <Flatpickr
                                options={{ mode: "multiple", locale: Portuguese, dateFormat: "Y-m-d", inline: true }}
                                value={selectedDates.map(d => d.date)}
                                onChange={handleCalendarChange}
                            />
                        </div>
                    </div>
                    <div className="w-full md:w-56 space-y-4">
                        <div className="bg-blue-50 p-5 rounded-xl border border-blue-100 text-center">
                            <label className="text-xs font-bold text-blue-400 uppercase mb-2 block">Vagas por dia</label>
                            <input type="number" min="1" value={defaultSeats} onChange={(e) => setDefaultSeats(e.target.value)} className="w-full p-3 bg-white border border-blue-200 rounded-xl text-center font-black text-3xl text-blue-600 focus:ring-4 focus:ring-blue-100 outline-none" />
                        </div>
                    </div>
                </div>
                )}

                {activeTab === 'list' && (
                <div className="max-h-[400px]">
                    {selectedDates.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-slate-300">
                            <Calendar size={48} className="mb-4 opacity-50"/>
                            <p>Nenhuma data selecionada ainda.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                            {selectedDates.map((item, idx) => (
                                <div key={item.date} className="flex items-center justify-between p-3 border border-slate-200 rounded-lg bg-slate-50 hover:border-blue-300 transition-colors">
                                    <div>
                                        <div className="font-bold text-slate-700">{format(parseISO(item.date), 'dd/MM/yyyy')}</div>
                                        <div className="text-xs text-slate-400">Vagas:</div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <input type="number" value={item.seats} min="1"
                                            onChange={(e) => updateSeats(idx, parseInt(e.target.value) || 1)}
                                            className="w-12 text-center border border-slate-300 rounded p-1 font-bold text-slate-700"
                                        />
                                        <button onClick={() => removeDate(idx)} className="text-slate-300 hover:text-red-500 transition-colors">
                                            <Trash2 size={18} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
                )}

                {activeTab === 'import' && (
                 <div className="space-y-4">
                     <textarea
                        className="w-full p-4 border border-slate-200 rounded-xl font-mono text-sm h-48 focus:ring-2 focus:ring-blue-100 outline-none resize-none"
                        placeholder={`15/05/2026  2`}
                        value={importText}
                        onChange={(e) => setImportText(e.target.value)}
                     ></textarea>
                     <button onClick={handleImport} className="w-full bg-green-600 text-white py-3 rounded-xl font-bold hover:bg-green-700 transition-colors flex justify-center gap-2">
                        <Check size={20} /> Processar Dados
                     </button>
                 </div>
                )}
            </div>

            {/* Footer */}
            <div className="bg-slate-50 p-4 border-t border-slate-100 flex justify-end shrink-0">
                <button onClick={() => setIsOpen(false)} className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-blue-500/20 transition-all hover:scale-[1.02]">
                    <Check size={20} /> Confirmar Seleção
                </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function TabButton({ active, onClick, icon: Icon, label }) {
  return (
    <button type="button" onClick={onClick} className={`flex items-center gap-2 px-4 py-3 text-sm font-bold rounded-t-lg transition-all border-b-2 ${active ? 'text-blue-600 border-blue-600 bg-white' : 'text-slate-400 border-transparent hover:text-slate-600 hover:bg-slate-100'}`}>
      <Icon size={16} /> {label}
    </button>
  );
}