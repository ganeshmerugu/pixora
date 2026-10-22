import React, { useState, useEffect } from 'react'
import { Plus, Trash2, FileJson } from 'lucide-react'
import { api } from '../api'

export default function Schemas() {
  const [schemas, setSchemas] = useState([])
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', doc_type: '', nodes: '' })

  const load = () => api.listSchemas().then(setSchemas).catch(() => {})

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    let nodes = []
    try { nodes = JSON.parse(form.nodes || '[]') } catch {}
    await api.createSchema({ name: form.name, doc_type: form.doc_type, nodes })
    setShowCreate(false)
    setForm({ name: '', doc_type: '', nodes: '' })
    load()
  }

  const handleDelete = async (id) => {
    await api.deleteSchema(id)
    load()
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Extraction Schemas</h2>
          <p className="text-sm text-zinc-500 mt-1">Ontology-guided extraction templates</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium">
          <Plus size={14} /> New Schema
        </button>
      </div>

      {showCreate && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 mb-6 space-y-3">
          <input placeholder="Schema name" value={form.name} onChange={e => setForm({...form, name: e.target.value})}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none" />
          <input placeholder="Document type (e.g., invoice)" value={form.doc_type} onChange={e => setForm({...form, doc_type: e.target.value})}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none" />
          <textarea placeholder='Nodes JSON: [{"name": "total", "field_type": "NUMBER"}]' value={form.nodes}
            onChange={e => setForm({...form, nodes: e.target.value})} rows={4}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm font-mono focus:border-indigo-500 focus:outline-none" />
          <div className="flex gap-2">
            <button onClick={handleCreate} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium">Create</button>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm">Cancel</button>
          </div>
        </div>
      )}

      {schemas.length === 0 ? (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
          <FileJson size={32} className="mx-auto text-zinc-600 mb-3" />
          <p className="text-sm text-zinc-500">No schemas yet</p>
          <p className="text-xs text-zinc-600 mt-1">Create extraction schemas to guide field extraction</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {schemas.map(s => (
            <div key={s.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium">{s.name}</h3>
                <button onClick={() => handleDelete(s.id)} className="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-rose-400">
                  <Trash2 size={14} />
                </button>
              </div>
              <p className="text-xs text-zinc-500 mb-2">Type: {s.doc_type} | Version: {s.version}</p>
              <p className="text-xs text-zinc-600">{s.nodes?.length || 0} fields defined</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
