import { Link } from 'react-router-dom'

/** Honest placeholder for screens that are designed (docs/design) but not built yet. */
export default function NotBuiltYet({ title = 'Not built yet', what }) {
  return (
    <div className="grid h-full place-items-center p-6">
      <div className="card max-w-md p-8">
        <h1 className="text-2xl">{title}</h1>
        {what && <p className="mt-2 text-[15px] text-muted">{what}</p>}
        <p className="mt-4 text-sm text-faint">This screen is designed but not built yet. It is planned for the 10 Nov prototype.</p>
        <Link to="/map" className="btn btn-primary mt-6">
          Back to the map
        </Link>
      </div>
    </div>
  )
}
