import React, { useState, useEffect } from 'react'
import { AlertTriangle, CheckCircle, XCircle, Eye } from 'lucide-react'
import { api } from '../api'

export default function ReviewQueue() {
  const [items, setItems] = useState([])

  useEffect(() => {
    api.getReviewQueue().then(setItems).catch(() => {})
  }, [])

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl">
      <div className="mb-6">
        <h2 className="text-2xl font-bold">Human Review Queue</h2>
        <p className="text-sm text-zinc-500 mt-1">Documents flagged for manual verification</p>
      </div>

      {items.length === 0 ? (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
          <CheckCircle size={32} className="mx-auto text-emerald-500/50 mb-3" />
          <p className="text-sm text-zinc-500">Review queue is empty</p>
          <p className="text-xs text-zinc-600 mt-1">Documents with low confidence scores will appear here</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map(item => (
            <div key={item.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`p-2 rounded-lg ${item.priority > 0 ? 'bg-amber-500/10' : 'bg-zinc-800'}`}>
                  <AlertTriangle size={16} className={item.priority > 0 ? 'text-amber-400' : 'text-zinc-500'} />
                </div>
                <div>
                  <p className="text-sm font-medium">Document {item.document_id?.slice(0, 16)}</p>
                  <p className="text-xs text-zinc-500">
                    Quality: {(item.quality_score * 100).toFixed(1)}% | {item.issues?.length || 0} issues
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${
                  item.status === 'pending' ? 'bg-amber-500/10 text-amber-400' :
                  item.status === 'approved' ? 'bg-emerald-500/10 text-emerald-400' :
                  'bg-zinc-800 text-zinc-500'
                }`}>
                  {item.status}
                </span>
                <button className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-indigo-400">
                  <Eye size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
