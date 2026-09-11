import { CompanionPanel } from "./CompanionPanel.jsx";

export function CompanionTab({ tab, active, visited, ports, theme }) {
  if (!visited) return null;
  return (
    <div hidden={!active}>
      <CompanionPanel tab={tab} ports={ports} theme={theme} />
    </div>
  );
}
