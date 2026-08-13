export const PublicContentRenderer = ({ entry, testIdPrefix = "public-content" }) => {
  if (!entry) return null;

  return (
    <div className="space-y-8" data-testid={`${testIdPrefix}-renderer`}>
      {entry.intro && (
        <p className="text-base md:text-lg leading-8 text-slate-300" data-testid={`${testIdPrefix}-intro`}>
          {entry.intro}
        </p>
      )}

      {(entry.sections || []).map((section, index) => (
        <section key={`${section.heading}-${index}`} className="space-y-4" data-testid={`${testIdPrefix}-section-${index}`}>
          <h2 className="font-serif-lux text-2xl text-white" data-testid={`${testIdPrefix}-section-heading-${index}`}>
            {section.heading}
          </h2>
          {(section.paragraphs || []).map((paragraph, pIndex) => (
            <p key={`${paragraph}-${pIndex}`} className="text-sm md:text-base leading-7 text-slate-300" data-testid={`${testIdPrefix}-section-paragraph-${index}-${pIndex}`}>
              {paragraph}
            </p>
          ))}
          {(section.bullets || []).length > 0 && (
            <ul className="space-y-2 text-sm md:text-base text-slate-200 list-disc pl-5" data-testid={`${testIdPrefix}-section-bullets-${index}`}>
              {section.bullets.map((bullet, bIndex) => (
                <li key={`${bullet}-${bIndex}`} data-testid={`${testIdPrefix}-section-bullet-${index}-${bIndex}`}>
                  {bullet}
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}

      {(entry.related_links || []).length > 0 && (
        <section className="space-y-4" data-testid={`${testIdPrefix}-related-links`}>
          <h2 className="font-serif-lux text-2xl text-white" data-testid={`${testIdPrefix}-related-links-heading`}>Conteúdos relacionados</h2>
          <div className="space-y-3">
            {entry.related_links.map((item, index) => (
              <a key={`${item.url}-${index}`} href={item.url} className="block rounded-2xl border border-white/10 bg-white/[0.03] p-4 hover:bg-white/[0.05] transition-colors" data-testid={`${testIdPrefix}-related-link-${index}`}>
                <p className="text-sm text-white font-medium">{item.title}</p>
                <p className="text-xs text-slate-400 mt-1">{item.reason}</p>
              </a>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};