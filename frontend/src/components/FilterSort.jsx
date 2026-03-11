import { SlidersHorizontal, ArrowUpDown } from 'lucide-react'

const RECOMMENDATIONS = ['All', 'Strong Fit', 'Maybe', 'Reject']
const SORT_OPTIONS = [
  { value: 'score_desc', label: 'Score: High → Low' },
  { value: 'score_asc', label: 'Score: Low → High' },
  { value: 'name_asc', label: 'Name: A → Z' },
]

export default function FilterSort({ filter, setFilter, sort, setSort, count }) {
  return (
    <div className="flex flex-wrap items-center gap-3 mb-6">
      <div className="flex items-center gap-1.5 text-xs text-navy-400 font-medium mr-1">
        <SlidersHorizontal size={13} />
        Filter:
      </div>
      {RECOMMENDATIONS.map(r => (
        <button
          key={r}
          onClick={() => setFilter(r)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all duration-200
            ${filter === r
              ? 'bg-navy-700 text-white border-navy-700'
              : 'bg-white text-navy-500 border-navy-200 hover:border-navy-400'
            }`}
        >
          {r}
        </button>
      ))}

      <div className="flex items-center gap-1.5 ml-auto">
        <ArrowUpDown size={13} className="text-navy-400" />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="select w-auto py-1.5 text-xs"
        >
          {SORT_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {count !== undefined && (
        <span className="text-xs text-navy-400 ml-1">{count} candidate{count !== 1 ? 's' : ''}</span>
      )}
    </div>
  )
}
