# Connection Rendering - Quick Test Guide

## Quick Validation (5 minutes)

### Test 1: Basic Connection (1 min)

1. Open canvas mode
2. Drag "Data Loader" from sidebar to canvas
3. Drag "Statistics Analyzer" to canvas (to the right)
4. Click output port (right side) of Data Loader
5. Click input port (left side) of Statistics Analyzer

**✅ Expected**: Line connects perfectly to port centers (no offset)

---

### Test 2: Zoom Test (2 min)

1. With connection from Test 1 still visible
2. Zoom IN: Ctrl + Scroll Up (or +) to 2.0x zoom
3. Zoom IN more: Continue to 3.0x zoom
4. Zoom OUT: Ctrl + Scroll Down (or -) to 0.5x zoom

**✅ Expected**: Line stays aligned to ports at ALL zoom levels

---

### Test 3: Pan Test (1 min)

1. With connection visible at any zoom level
2. Click and drag canvas background to pan left
3. Pan right
4. Pan up
5. Pan down

**✅ Expected**: Connection moves with nodes, stays aligned

---

### Test 4: Drag Node (1 min)

1. Click and drag a node that has connections
2. Move it around the canvas
3. Release mouse

**✅ Expected**:

- Connection updates in real-time while dragging
- Final position perfectly aligned

---

## Extended Validation (Optional - 10 minutes)

### Test 5: Connection Dragging

1. Click output port to start new connection
2. Move mouse around canvas (without clicking)
3. Try at different zoom levels (1.0x, 2.0x, 0.5x)
4. Try with canvas panned to different positions
5. Complete connection or press Escape to cancel

**✅ Expected**: Temporary line follows cursor accurately at all times

---

### Test 6: Multiple Connections

1. Create pipeline: Data Loader → Statistics Analyzer → Model Trainer
2. Zoom to 2.5x
3. Pan canvas to upper-left corner
4. Drag Data Loader node
5. Drag Model Trainer node

**✅ Expected**: Both connections update correctly, stay aligned

---

### Test 7: Session Persistence

1. Create 2-3 connected nodes
2. Pan canvas to (-200, -300)
3. Zoom to 1.8x
4. Save session (connections auto-saved)
5. Create new session
6. Switch back to first session

**✅ Expected**: Connections restored perfectly, pan/zoom state preserved

---

### Test 8: Edge Cases

1. **Maximum Zoom**: Zoom to 5.0x → Connections still aligned?
2. **Minimum Zoom**: Zoom to 0.25x → Connections still aligned?
3. **Large Pan**: Pan to (-1000, -1000) → Connections still aligned?
4. **Canvas Boundary**: Place nodes at edges → Connections work?

**✅ Expected**: All edge cases render correctly

---

## Known Issues (Pre-Fix)

Before the fix, these would FAIL:

❌ **Zoom Bug**: Lines offset from ports at zoom ≠ 1.0x  
❌ **Pan Bug**: Connections "jump" when panning  
❌ **Drag Bug**: Temporary line doesn't follow cursor during pan/zoom  
❌ **Restore Bug**: Connections appear offset after session reload with zoom

## After Fix - All Should Pass

After the CONNECTION_RENDERING_FIX implementation:

✅ All zoom levels work correctly  
✅ Pan doesn't affect connection alignment  
✅ Temporary line follows cursor accurately  
✅ Session restore maintains perfect alignment

---

## Visual Reference

### Correct Behavior

```
  ┌─────────┐         ┌─────────┐
  │ Node A  ├────────→│ Node B  │
  └─────────┘         └─────────┘
     ↑                    ↑
     Line connects      Line connects
     to port center     to port center
```

### Buggy Behavior (Pre-Fix)

```
  ┌─────────┐
  │ Node A  │
  └─────────┘ ╲
               ╲
                ╲      ┌─────────┐
                 `────→│ Node B  │
                       └─────────┘
     Line offset from port centers!
```

---

## Performance Check

### Before Fix

- Pan/Zoom: Laggy with 10+ connections
- Visual stutter during rapid zoom

### After Fix

- Pan/Zoom: Smooth at any connection count
- No visual stutter (CSS transforms only)

---

## Quick Troubleshooting

### If connections still appear buggy:

1. **Hard Refresh**: Ctrl + Shift + R to clear cache
2. **Check Console**: Look for JavaScript errors
3. **Verify File**: Ensure `ConnectionManager.js` has latest changes
4. **Check Transform**: Inspect SVG overlay element in DevTools
   - Should have: `transform: translate(Xpx, Ypx) scale(Z)`
5. **Check Node Data**: Nodes should have `dataset.originalX` and `dataset.originalY`

### Debug Commands (Browser Console)

```javascript
// Check SVG overlay transform
document.querySelector(".connection-overlay").style.transform;

// Check node positions
document
  .querySelectorAll(".agent-node")
  .forEach((n) =>
    console.log(n.dataset.instanceId, n.dataset.originalX, n.dataset.originalY)
  );

// Check connections
connectionManager.getConnectionsData();
```

---

## Success Criteria

✅ **All Tests Pass**  
✅ **No Console Errors**  
✅ **Smooth Visual Experience**  
✅ **Accurate Port Alignment**

---

**Test Duration**: 5-15 minutes  
**Difficulty**: Easy  
**Prerequisites**: Backend + Frontend running, session with agents

**Status**: Ready for Testing ✅
