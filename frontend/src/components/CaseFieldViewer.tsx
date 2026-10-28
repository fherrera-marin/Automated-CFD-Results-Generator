import { useState } from 'react'
import { api, FIELD_LABELS, type FieldName } from '../api/client'

export default function CaseFieldViewer({ runId, caseId }: { runId: number; caseId: number }) {
  const [field, setField] = useState<FieldName>('p')
  // Bust the browser cache when switching fields/cases so the <img> always
  // reflects this case's latest resultados.csv rather than a stale render.
  const [nonce, setNonce] = useState(0)
  // The backend renders this PNG on demand (interpolating the case's
  // resultados.csv), which takes a moment -- show a loading message instead
  // of a blank/broken-looking image while that's in flight.
  const [isLoading, setIsLoading] = useState(true)

  // The real backend's URL already has `?field=...`, so the cache-buster
  // needs `&`; the static demo build's URL is a plain file path with no
  // query string at all, so it needs `?` instead -- blindly using `&` there
  // produced an invalid path like "case41_p.png&_=0" that 404s.
  const baseUrl = api.caseFieldUrl(runId, caseId, field)
  const src = `${baseUrl}${baseUrl.includes('?') ? '&' : '?'}_=${nonce}`

  return (
    <div className="field-viewer">
      <div className="field-viewer-controls">
        {(Object.keys(FIELD_LABELS) as FieldName[]).map((f) => (
          <label key={f} className="field-radio">
            <input
              type="radio"
              name={`field-${caseId}`}
              checked={field === f}
              onChange={() => {
                setField(f)
                setNonce((n) => n + 1)
                setIsLoading(true)
              }}
            />
            {FIELD_LABELS[f]}
          </label>
        ))}
      </div>
      {isLoading && <p className="muted field-viewer-loading">Cargando vista…</p>}
      <img
        key={src}
        src={src}
        alt={`${FIELD_LABELS[field]} heatmap`}
        className="field-viewer-img"
        style={isLoading ? { display: 'none' } : undefined}
        onLoad={() => setIsLoading(false)}
        onError={() => setIsLoading(false)}
      />
    </div>
  )
}
