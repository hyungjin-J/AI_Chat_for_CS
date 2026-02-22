import type { ReactNode } from "react";

type SectionPanelProps = {
    title: string;
    subtitle?: string;
    actions?: ReactNode;
    children: ReactNode;
};

export function SectionPanel({ title, subtitle, actions, children }: SectionPanelProps) {
    return (
        <section className="section-panel">
            <header className="section-panel__header">
                <div>
                    <h2>{title}</h2>
                    {subtitle ? <p>{subtitle}</p> : null}
                </div>
                {actions ? <div className="section-panel__actions">{actions}</div> : null}
            </header>
            {children}
        </section>
    );
}
