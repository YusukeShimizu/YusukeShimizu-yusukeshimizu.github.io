---
date: '2025-03-28T00:00:00+09:00'
title: 'なぜ我々は MCP に全力投球しているのか'
---

https://mastra.ai/blog/mastra-mcp からのllmを用いた意訳である

---

AI エージェント向けツール統合の現状は混沌としている。「MCP Calendar integration」の検索結果からも明らかなように、どの実装が最適かを判断する統一基準がない。ツールの発見、インストール、設定は未解決の課題である。

Mastra では、この問題に取り組み、Anthropic の Model Context Protocol (MCP) が **エージェントとツールの相互作用の将来** であると確信している。

## 競合する標準規格

現在、複数のアプローチが競合している：

### Agents.json (Wildcard)

[Agents.json](https://docs.wild-card.ai/agentsjson/introduction)は OpenAPI を拡張し、LLM 向けに API 相互作用を最適化する。開発者向け API と LLM 用 API の乖離に対処し、既存 API に文脈情報を補完する。

### Composio

[Composio](https://composio.dev)は独自仕様と豊富な統合ライブラリを提供している。最近は[MCP サポートも追加](https://x.com/composiohq/status/1896968949654495291)し、選択肢を広げた。

### Model Context Protocol (MCP)

[MCP](https://modelcontextprotocol.io/introduction)は Anthropic 管理のオープンスタンダードであり、OSS コミュニティの協力で構築されている。AI アプリケーションの「USB-C ポート」として、LLM を外部ツールに接続する標準インターフェースを提供する。

## MCP の課題

MCP エコシステムの主な課題は3つある：

1. **Discovery**: ツール発見のための標準化された方法がない
2. **Quality**: 集中管理されたレジストリや検証プロセスがない
3. **Configuration**: 各プロバイダーが独自の設定スキーマを持つ

Shopify CEO の Tobi Lütke は[MCP を「LLM ツールの USB-C」](https://x.com/tobi/status/1891137636720419191)と表現しつつも、まだプロトコルだけで「プラグ」が欠けていると指摘している。

コミュニティは [Official Registry](https://github.com/orgs/modelcontextprotocol/discussions/159) や [`.well-known/mcp.json`](https://github.com/orgs/modelcontextprotocol/discussions/84) などの規格で問題解決に取り組んでいる。

## MCP の優位性

MCP には明確な利点がある：

1. **オープン性**: 業界全体のプロトコルとして設計され、ベンダー非依存
2. **業界採用**: Zed、Replit、Codeium、Sourcegraph、Cursor などが実装
3. **互換性**: 他標準とのブリッジが可能
4. **活発な開発**: コミュニティによる継続的な機能拡張

## Mastra の提案

Mastra では、フレームワークフレンドリーな MCP 統合を提案している。主な要素は：

1. **レジストリクライアント**: ツールレジストリと標準的に相互作用するためのクライアント
2. **設定と検証**: サーバー定義の標準形式による設定スキーマの公開
3. **フレームワークレベル設定**: 任意のレジストリに接続できる統一 API

```javascript
import { MCPConfiguration } from "@mastra/mcp";

const configuration = new MCPConfiguration({
  registry: "https://mcp.run/.well-known/mcp.json",
  servers: {
    googleCalendar: {
      // Google カレンダー MCP サーバー設定
    }
  }
});

// 構成を Mastra エージェントに適用
const toolsets = await configuration.getConnectedTools();
const response = await agent.stream(prompt, { toolsets });
```

## 今後の展望

AI ツール統合はパッケージ管理の黎明期に似ている。`npm install` が JavaScript のパッケージ管理を変革したように、MCP は AI エージェントとツールの相互作用を標準化する可能性を持つ。

Mastra のロードマップ:
1. MCP サーバー向け標準インストール・設定フローの構築
2. 仕様進化に応じた機能拡張
3. ツール発見・設定のためのプリミティブ開発

MCP の標準化により、ツールの発見、設定、安全な利用が容易になるエコシステムの構築が可能になる。 