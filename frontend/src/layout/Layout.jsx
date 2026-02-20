import { Box, Drawer, List, ListItem, ListItemText } from "@mui/material";
import { Outlet, useNavigate } from "react-router-dom";

const drawerWidth = 240;

function Layout() {
  const navigate = useNavigate();

  const menu = [
    { label: "Dashboard", path: "/" },
    { label: "Titles", path: "/titles" },
    { label: "Campaigns", path: "/campaigns" },
    { label: "Keywords", path: "/keywords" },
    { label: "Products", path: "/products" },
    { label: "Reports", path: "/reports" }
  ];

  return (
    <Box sx={{ display: "flex" }}>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          "& .MuiDrawer-paper": { width: drawerWidth }
        }}
      >
        <List>
          {menu.map((item) => (
            <ListItem button key={item.label} onClick={() => navigate(item.path)}>
              <ListItemText primary={item.label} />
            </ListItem>
          ))}
        </List>
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Outlet />
      </Box>
    </Box>
  );
}

export default Layout;
