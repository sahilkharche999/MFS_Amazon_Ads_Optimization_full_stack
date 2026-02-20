import { Grid, Card, CardContent, Typography } from "@mui/material";

function KPICards({ data }) {
  const cards = [
    { label: "Impressions", value: data.impressions },
    { label: "Clicks", value: data.clicks },
    { label: "CTR %", value: data.ctr },
    { label: "Spend ($)", value: data.spend },
    { label: "Orders", value: data.orders },
    { label: "Cost / Order", value: data.cpo },
  ];

  return (
    <Grid container spacing={2}>
      {cards.map((card, i) => (
        <Grid item xs={12} md={2} key={i}>
          <Card elevation={3}>
            <CardContent>
              <Typography variant="subtitle2">
                {card.label}
              </Typography>
              <Typography variant="h5">
                {card.value}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}

export default KPICards;
