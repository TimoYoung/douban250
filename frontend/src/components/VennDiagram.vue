<template>
  <div class="venn-wrapper">
    <svg viewBox="0 0 420 160" class="venn-svg">
      <circle :cx="155" :cy="80" :r="75" :fill="colorAFill" :stroke="colorA" stroke-width="1.5"/>
      <circle :cx="265" :cy="80" :r="75" :fill="colorBFill" :stroke="colorB" stroke-width="1.5" :stroke-dasharray="dashed ? '4 2' : undefined"/>
      <text :x="105" y="75" text-anchor="middle" class="venn-num">{{ onlyA }}</text>
      <text :x="105" y="95" text-anchor="middle" class="venn-sub">{{ labelA }}</text>
      <text :x="210" y="75" text-anchor="middle" class="venn-num venn-center-num">{{ both }}</text>
      <text :x="210" y="95" text-anchor="middle" class="venn-sub">{{ labelCenter }}</text>
      <text :x="315" y="75" text-anchor="middle" class="venn-num">{{ onlyB }}</text>
      <text :x="315" y="95" text-anchor="middle" class="venn-sub">{{ labelB }}</text>
    </svg>
  </div>
</template>

<script setup>
defineProps({
  onlyA: { type: Number, default: 0 },
  both: { type: Number, default: 0 },
  onlyB: { type: Number, default: 0 },
  labelA: { type: String, default: '仅豆瓣' },
  labelCenter: { type: String, default: '共有' },
  labelB: { type: String, default: '仅IMDb' },
  colorA: { type: String, default: '#1890ff' },
  colorB: { type: String, default: '#d97706' },
  colorAFill: { type: String, default: 'rgba(24,144,255,0.12)' },
  colorBFill: { type: String, default: 'rgba(217,119,6,0.12)' },
  dashed: { type: Boolean, default: false },
})
</script>

<style scoped>
.venn-wrapper {
  text-align: center;
}
.venn-svg {
  width: 360px;
  height: 140px;
}
.venn-num {
  font-size: 20px;
  font-weight: 700;
  fill: #18181b;
  font-family: 'SF Mono', monospace;
}
.venn-center-num {
  fill: #6366f1;
}
.venn-sub {
  font-size: 10px;
  fill: #71717a;
}
</style>
