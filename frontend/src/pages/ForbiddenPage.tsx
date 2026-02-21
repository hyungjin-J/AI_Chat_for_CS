import { Link } from "react-router-dom";

export function ForbiddenPage() {
    return (
        <main className="forbidden-page">
            <h1>403 Forbidden</h1>
            <p>You do not have permission to access this page.</p>
            <Link to="/login">Back to login</Link>
        </main>
    );
}

